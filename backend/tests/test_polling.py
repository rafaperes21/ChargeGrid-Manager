import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.integracoes.polling import PollingService
from app.integracoes.sems_client import SemsClient
from app.models.charger import Charger, ChargerReading
from app.models.enums import ChargerModel, ChargerStatus, ChargingSessionStatus, UserRole
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.models.user import User
from app.schemas.charger_reading import ChargerReadingContract


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


class _FakeSemsClient(SemsClient):
    """Devolve exatamente as leituras que o teste passar, sem tocar banco."""

    def __init__(self, readings_by_call: list[list[ChargerReadingContract]] | None = None):
        self.readings_by_call = readings_by_call or []
        self.calls = 0

    async def fetch_readings(self, charger_serials, db):
        self.calls += 1
        if self.readings_by_call:
            return self.readings_by_call.pop(0)
        return []


class _FailingSemsClient(SemsClient):
    async def fetch_readings(self, charger_serials, db):
        raise ConnectionError("SEMS+ indisponivel neste teste")


@pytest.fixture
def establishment(db_session):
    owner = _make_user(db_session, role=UserRole.owner)
    return _make_establishment(db_session, owner)


def test_poll_once_sem_carregadores_nao_faz_nada(db_session):
    service = PollingService(_FakeSemsClient())
    _run(service.poll_once(db_session))
    assert service.consecutive_failures == 0


def test_poll_once_persiste_leitura_e_sincroniza_status_de_carregador_ocioso(
    db_session, establishment
):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.offline)
    now = datetime.now(UTC)
    fake = _FakeSemsClient(
        [
            [
                ChargerReadingContract(
                    charger_serial=charger.sems_serial,
                    timestamp=now,
                    power_kw=Decimal("0.000"),
                    status=ChargerStatus.livre,
                    total_energy_kwh=Decimal("12.500"),
                )
            ]
        ]
    )
    service = PollingService(fake)

    _run(service.poll_once(db_session))

    readings = (
        db_session.query(ChargerReading).filter(ChargerReading.charger_id == charger.id).all()
    )
    assert len(readings) == 1
    assert readings[0].total_energy_kwh == Decimal("12.500")
    db_session.refresh(charger)
    assert charger.status == ChargerStatus.livre


def test_poll_once_nao_sobrescreve_status_de_carregador_com_sessao_aberta(
    db_session, establishment
):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    user = _make_user(db_session)
    session = ChargingSession(
        user_id=user.id,
        charger_id=charger.id,
        establishment_id=establishment.id,
        status=ChargingSessionStatus.pending,
        started_at=datetime.now(UTC),
    )
    db_session.add(session)
    db_session.commit()

    now = datetime.now(UTC)
    fake = _FakeSemsClient(
        [
            [
                ChargerReadingContract(
                    charger_serial=charger.sems_serial,
                    timestamp=now,
                    power_kw=Decimal("0.000"),
                    status=ChargerStatus.livre,  # curva ainda na rampa, reporta livre
                    total_energy_kwh=Decimal("0.000"),
                )
            ]
        ]
    )
    service = PollingService(fake)

    _run(service.poll_once(db_session))

    db_session.refresh(charger)
    # nao pode ter voltado pra livre so por causa de uma leitura ociosa - a sessao ainda
    # e dona do status desse carregador.
    assert charger.status == ChargerStatus.reservado


def test_poll_once_e_idempotente_para_a_mesma_leitura(db_session, establishment):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    now = datetime.now(UTC)
    reading = ChargerReadingContract(
        charger_serial=charger.sems_serial,
        timestamp=now,
        power_kw=Decimal("3.500"),
        status=ChargerStatus.carregando,
        total_energy_kwh=Decimal("1.000"),
    )
    fake = _FakeSemsClient([[reading], [reading]])
    service = PollingService(fake)

    _run(service.poll_once(db_session))
    _run(service.poll_once(db_session))

    rows = (
        db_session.query(ChargerReading)
        .filter(ChargerReading.charger_id == charger.id, ChargerReading.timestamp == now)
        .all()
    )
    assert len(rows) == 1


def test_poll_once_marca_offline_apos_n_falhas_consecutivas(db_session, establishment):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    service = PollingService(_FailingSemsClient(), offline_after_failures=3)

    _run(service.poll_once(db_session))
    db_session.refresh(charger)
    assert charger.status == ChargerStatus.livre  # ainda nao bateu o limite
    assert service.consecutive_failures == 1

    _run(service.poll_once(db_session))
    _run(service.poll_once(db_session))

    db_session.refresh(charger)
    assert charger.status == ChargerStatus.offline
    assert service.consecutive_failures == 3


def test_sucesso_depois_de_falhas_zera_o_contador(db_session, establishment):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    failing = _FailingSemsClient()
    service = PollingService(failing, offline_after_failures=5)

    _run(service.poll_once(db_session))
    _run(service.poll_once(db_session))
    assert service.consecutive_failures == 2

    now = datetime.now(UTC)
    service.sems_client = _FakeSemsClient(
        [
            [
                ChargerReadingContract(
                    charger_serial=charger.sems_serial,
                    timestamp=now,
                    power_kw=Decimal("0.000"),
                    status=ChargerStatus.livre,
                    total_energy_kwh=Decimal("0.000"),
                )
            ]
        ]
    )
    _run(service.poll_once(db_session))
    assert service.consecutive_failures == 0
