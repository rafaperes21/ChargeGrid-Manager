import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

import app.integracoes.sems_client as sems_client_module
from app.integracoes.sems_client import RealSemsClient, get_sems_client
from app.integracoes.simulated_sems_client import SimulatedSemsClient
from app.models.charger import Charger
from app.models.enums import ChargerModel, ChargerStatus, ChargingSessionStatus, UserRole
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.models.user import User


def _run(coro):
    return asyncio.run(coro)


def _make_user(db, *, role: UserRole = UserRole.customer) -> User:
    user = User(
        email=f"{uuid.uuid4().hex[:10]}@teste.com",
        role=role,
        full_name="Fulano",
        rfid_virtual_id=f"rfid-{uuid.uuid4().hex[:8]}",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_establishment(db, owner: User) -> Establishment:
    establishment = Establishment(
        owner_id=owner.id,
        name="Estacionamento Teste",
        kind="estacionamento",
        phase="trifasico",
        grid_connection_kw=Decimal("75.000"),
        power_limit_kw=Decimal("40.000"),
    )
    db.add(establishment)
    db.commit()
    db.refresh(establishment)
    return establishment


def _make_charger(db, establishment: Establishment, *, status: ChargerStatus) -> Charger:
    charger = Charger(
        establishment_id=establishment.id,
        sems_serial=f"SN-{uuid.uuid4().hex[:8]}",
        model=ChargerModel.gw7k,
        spot_label="A1",
        status=status,
        nominal_power_kw=Decimal("11.000"),
    )
    db.add(charger)
    db.commit()
    db.refresh(charger)
    return charger


def _make_open_session(db, charger: Charger, user: User, started_at: datetime) -> ChargingSession:
    session = ChargingSession(
        user_id=user.id,
        charger_id=charger.id,
        establishment_id=charger.establishment_id,
        status=ChargingSessionStatus.pending,
        started_at=started_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def establishment(db_session):
    owner = _make_user(db_session, role=UserRole.owner)
    return _make_establishment(db_session, owner)


def test_carregador_sem_sessao_fica_ocioso(db_session, establishment):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    client = SimulatedSemsClient()

    readings = _run(client.fetch_readings([charger.sems_serial], db_session))

    assert len(readings) == 1
    reading = readings[0]
    assert reading.power_kw == Decimal("0.000")
    assert reading.status == ChargerStatus.livre
    assert reading.charger_serial == charger.sems_serial


def test_carregador_com_sessao_pending_gera_potencia_conforme_o_tempo_decorrido(
    db_session, establishment
):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    user = _make_user(db_session)
    started_at = datetime.now(UTC) - timedelta(seconds=90)
    _make_open_session(db_session, charger, user, started_at)

    client = SimulatedSemsClient()
    readings = _run(client.fetch_readings([charger.sems_serial], db_session))

    assert len(readings) == 1
    # 90s depois do inicio ja passou o suficiente da rampa (0-2min) - potencia deve ser
    # > 0 e o status carregando.
    assert readings[0].power_kw > Decimal("0.000")
    assert readings[0].status == ChargerStatus.carregando


def test_mesma_sessao_gera_a_mesma_curva_em_polls_repetidos(db_session, establishment):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    user = _make_user(db_session)
    started_at = datetime.now(UTC) - timedelta(seconds=30)
    _make_open_session(db_session, charger, user, started_at)

    client = SimulatedSemsClient()
    first = _run(client.fetch_readings([charger.sems_serial], db_session))
    second = _run(client.fetch_readings([charger.sems_serial], db_session))

    # mesmo instante decorrido (poll muito rapido) -> mesma amostra da curva
    assert first[0].power_kw == second[0].power_kw


def test_total_energy_kwh_acumula_de_forma_monotonica(db_session, establishment):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    user = _make_user(db_session)
    started_at = datetime.now(UTC) - timedelta(minutes=3)
    _make_open_session(db_session, charger, user, started_at)

    client = SimulatedSemsClient()
    first = _run(client.fetch_readings([charger.sems_serial], db_session))
    second = _run(client.fetch_readings([charger.sems_serial], db_session))

    assert second[0].total_energy_kwh >= first[0].total_energy_kwh


def test_sessao_com_curva_esgotada_some_do_cache_e_fica_ociosa(db_session, establishment):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    user = _make_user(db_session)
    # sessao "iniciada" ha muito tempo - qualquer curva gerada ja teria terminado
    started_at = datetime.now(UTC) - timedelta(hours=5)
    session = _make_open_session(db_session, charger, user, started_at)

    client = SimulatedSemsClient()
    readings = _run(client.fetch_readings([charger.sems_serial], db_session))

    assert readings[0].power_kw == Decimal("0.000")
    assert readings[0].status == ChargerStatus.livre
    assert session.id not in client._samples_by_session


def test_real_sems_client_e_stub():
    client = RealSemsClient()
    with pytest.raises(NotImplementedError):
        _run(client.fetch_readings(["SN-1"], db=None))


def test_get_sems_client_despacha_pelo_settings(monkeypatch):
    sems_client_module._client = None
    monkeypatch.setattr(sems_client_module.settings, "sems_source", "simulator")
    assert isinstance(get_sems_client(), SimulatedSemsClient)

    sems_client_module._client = None
    monkeypatch.setattr(sems_client_module.settings, "sems_source", "real")
    assert isinstance(get_sems_client(), RealSemsClient)

    sems_client_module._client = None
    monkeypatch.setattr(sems_client_module.settings, "sems_source", "inexistente")
    with pytest.raises(ValueError):
        get_sems_client()

    sems_client_module._client = None
