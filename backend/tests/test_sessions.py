import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.charger import Charger, ChargerReading
from app.models.enums import ChargerModel, ChargerStatus, ChargingSessionStatus, PlanKind, UserRole
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.models.tariff import Plan, TariffRule
from app.models.user import Subscription, User
from app.services.pricing import calculate_session_amount
from app.services.sessions import (
    LOCAL_TZ,
    build_receipt,
    start_session,
    sync_session,
)

_UTC = UTC


def _make_user(db, *, role: UserRole, email: str, rfid: str | None = "rfid-1") -> User:
    user = User(email=email, role=role, full_name="Fulano", rfid_virtual_id=rfid)
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
        nominal_power_kw=Decimal("7.000"),
    )
    db.add(charger)
    db.commit()
    db.refresh(charger)
    return charger


def _make_full_day_tariff(
    db, establishment: Establishment, started_at: datetime, price: Decimal
) -> TariffRule:
    """Regra cobrindo o dia inteiro do `started_at` (em horario local), pra nao depender
    de qual dia da semana o teste roda."""
    local_weekday = started_at.astimezone(LOCAL_TZ).weekday()
    rule = TariffRule(
        establishment_id=establishment.id,
        name="Unica",
        days_of_week=str(local_weekday),
        start_time_local=datetime.min.time(),
        end_time_local=datetime.max.time().replace(microsecond=0),
        price_per_kwh=price,
        is_special=False,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def _add_reading(db, charger: Charger, timestamp: datetime, power_kw: Decimal) -> ChargerReading:
    reading = ChargerReading(
        charger_id=charger.id,
        timestamp=timestamp,
        power_kw=power_kw,
        status=ChargerStatus.carregando if power_kw > 0 else ChargerStatus.livre,
    )
    db.add(reading)
    db.commit()
    return reading


@pytest.fixture
def owner(db_session):
    return _make_user(db_session, role=UserRole.owner, email="dono@teste.com", rfid=None)


@pytest.fixture
def customer(db_session):
    return _make_user(db_session, role=UserRole.customer, email="cliente@teste.com")


@pytest.fixture
def establishment(db_session, owner):
    return _make_establishment(db_session, owner)


# ---------------------------------------------------------------------------
# start_session
# ---------------------------------------------------------------------------


def test_start_session_cria_pending_e_reserva_o_carregador(db_session, establishment, customer):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)

    session = start_session(db_session, customer, charger.id)

    assert session.status == ChargingSessionStatus.pending
    assert session.user_id == customer.id
    assert session.establishment_id == establishment.id
    assert charger.status == ChargerStatus.reservado


def test_start_session_falha_sem_rfid_cadastrado(db_session, establishment):
    user_sem_rfid = _make_user(
        db_session, role=UserRole.customer, email="sem-rfid@teste.com", rfid=None
    )
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)

    with pytest.raises(HTTPException) as exc:
        start_session(db_session, user_sem_rfid, charger.id)
    assert exc.value.status_code == 400


def test_start_session_falha_se_carregador_nao_livre(db_session, establishment, customer):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.carregando)

    with pytest.raises(HTTPException) as exc:
        start_session(db_session, customer, charger.id)
    assert exc.value.status_code == 409


def test_start_session_falha_se_usuario_ja_tem_sessao_aberta(db_session, establishment, customer):
    charger1 = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    charger2 = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    start_session(db_session, customer, charger1.id)

    with pytest.raises(HTTPException) as exc:
        start_session(db_session, customer, charger2.id)
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# sync_session - transicoes de estado
# ---------------------------------------------------------------------------


def test_sync_session_timeout_sem_potencia_vira_error(db_session, establishment, customer):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    started_at = datetime.now(_UTC) - timedelta(minutes=6)
    session = ChargingSession(
        user_id=customer.id,
        charger_id=charger.id,
        establishment_id=establishment.id,
        status=ChargingSessionStatus.pending,
        started_at=started_at,
    )
    db_session.add(session)
    db_session.commit()

    result = sync_session(db_session, session)

    assert result.status == ChargingSessionStatus.error
    assert result.amount_due is None
    assert charger.status == ChargerStatus.livre


def test_sync_session_pending_ainda_dentro_do_timeout_nao_muda(db_session, establishment, customer):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    started_at = datetime.now(_UTC) - timedelta(minutes=1)
    session = ChargingSession(
        user_id=customer.id,
        charger_id=charger.id,
        establishment_id=establishment.id,
        status=ChargingSessionStatus.pending,
        started_at=started_at,
    )
    db_session.add(session)
    db_session.commit()

    result = sync_session(db_session, session)

    assert result.status == ChargingSessionStatus.pending
    assert charger.status == ChargerStatus.reservado


def test_sync_session_ativa_e_acumula_energia_por_trapezio(db_session, establishment, customer):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    started_at = datetime.now(_UTC) - timedelta(minutes=10)
    session = ChargingSession(
        user_id=customer.id,
        charger_id=charger.id,
        establishment_id=establishment.id,
        status=ChargingSessionStatus.pending,
        started_at=started_at,
    )
    db_session.add(session)
    db_session.commit()

    _add_reading(db_session, charger, started_at + timedelta(minutes=1), Decimal("3.000"))
    _add_reading(db_session, charger, started_at + timedelta(minutes=2), Decimal("6.000"))
    _add_reading(db_session, charger, started_at + timedelta(minutes=3), Decimal("6.000"))

    result = sync_session(db_session, session)

    assert result.status == ChargingSessionStatus.active
    assert charger.status == ChargerStatus.carregando
    # (3+6)/2 * 1min + (6+6)/2 * 1min, em horas
    assert result.energy_kwh == Decimal("0.175")


def test_sync_session_fecha_por_potencia_zerada_e_calcula_valor(
    db_session, establishment, customer
):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    started_at = datetime.now(_UTC) - timedelta(minutes=10)
    tariff_rate = Decimal("2.0000")
    tariff = _make_full_day_tariff(db_session, establishment, started_at, tariff_rate)

    session = ChargingSession(
        user_id=customer.id,
        charger_id=charger.id,
        establishment_id=establishment.id,
        status=ChargingSessionStatus.pending,
        started_at=started_at,
    )
    db_session.add(session)
    db_session.commit()

    r1 = started_at + timedelta(minutes=1)
    r2 = started_at + timedelta(minutes=2)
    r3 = started_at + timedelta(minutes=3)
    r4 = started_at + timedelta(minutes=4)
    r5 = started_at + timedelta(minutes=5)
    _add_reading(db_session, charger, r1, Decimal("3.000"))
    _add_reading(db_session, charger, r2, Decimal("6.000"))
    _add_reading(db_session, charger, r3, Decimal("6.000"))
    _add_reading(db_session, charger, r4, Decimal("0.030"))
    _add_reading(db_session, charger, r5, Decimal("0.000"))

    result = sync_session(db_session, session)

    assert result.status == ChargingSessionStatus.finished
    assert result.ended_at.replace(tzinfo=_UTC) == r5
    assert result.tariff_rule_id == tariff.id
    assert result.tariff_rate_applied == tariff_rate
    assert result.plan_discount_pct == Decimal("0")
    assert charger.status == ChargerStatus.livre

    duration_minutes = Decimal((r5 - started_at).total_seconds()) / Decimal("60")
    expected = calculate_session_amount(
        energy_kwh=result.energy_kwh,
        tariff_rate_per_kwh=tariff_rate,
        session_duration_minutes=duration_minutes,
        free_minutes=0,
        plan_discount_pct=Decimal("0"),
        franquia_kwh_available=Decimal("0"),
    )
    assert result.amount_due == expected.final_amount

    receipt = build_receipt(result)
    assert receipt["session_id"] == str(result.id)
    assert receipt["amount_due"] == str(result.amount_due)


def test_sync_session_sem_tarifa_configurada_vira_error_sem_cobranca(
    db_session, establishment, customer
):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    started_at = datetime.now(_UTC) - timedelta(minutes=10)
    # nenhuma TariffRule criada para o estabelecimento

    session = ChargingSession(
        user_id=customer.id,
        charger_id=charger.id,
        establishment_id=establishment.id,
        status=ChargingSessionStatus.pending,
        started_at=started_at,
    )
    db_session.add(session)
    db_session.commit()

    _add_reading(db_session, charger, started_at + timedelta(minutes=1), Decimal("3.000"))
    _add_reading(db_session, charger, started_at + timedelta(minutes=2), Decimal("0.000"))
    _add_reading(db_session, charger, started_at + timedelta(minutes=3), Decimal("0.000"))

    result = sync_session(db_session, session)

    assert result.status == ChargingSessionStatus.error
    assert result.amount_due is None
    assert charger.status == ChargerStatus.livre


def test_sync_session_aplica_desconto_do_plano_e_franquia(db_session, establishment, customer):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    started_at = datetime.now(_UTC) - timedelta(minutes=10)
    tariff_rate = Decimal("2.0000")
    _make_full_day_tariff(db_session, establishment, started_at, tariff_rate)

    plan = Plan(
        establishment_id=establishment.id,
        name="Mensal",
        kind=PlanKind.mensal,
        price=Decimal("49.90"),
        free_kwh_allowance=Decimal("0.100"),
        discount_pct=Decimal("15"),
        priority=1,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    subscription = Subscription(
        user_id=customer.id,
        plan_id=plan.id,
        billing_cycle_start=date.today(),
        billing_cycle_end=None,
        active=True,
    )
    db_session.add(subscription)
    db_session.commit()

    session = ChargingSession(
        user_id=customer.id,
        charger_id=charger.id,
        establishment_id=establishment.id,
        status=ChargingSessionStatus.pending,
        started_at=started_at,
    )
    db_session.add(session)
    db_session.commit()

    r1 = started_at + timedelta(minutes=1)
    r2 = started_at + timedelta(minutes=2)
    r3 = started_at + timedelta(minutes=3)
    r4 = started_at + timedelta(minutes=4)
    _add_reading(db_session, charger, r1, Decimal("6.000"))
    _add_reading(db_session, charger, r2, Decimal("6.000"))
    _add_reading(db_session, charger, r3, Decimal("0.000"))
    _add_reading(db_session, charger, r4, Decimal("0.000"))

    result = sync_session(db_session, session)

    assert result.status == ChargingSessionStatus.finished
    assert result.plan_discount_pct == Decimal("15")

    duration_minutes = Decimal((r4 - started_at).total_seconds()) / Decimal("60")
    expected = calculate_session_amount(
        energy_kwh=result.energy_kwh,
        tariff_rate_per_kwh=tariff_rate,
        session_duration_minutes=duration_minutes,
        free_minutes=0,
        plan_discount_pct=Decimal("15"),
        franquia_kwh_available=Decimal("0.100"),
    )
    assert result.amount_due == expected.final_amount


def test_build_receipt_exige_sessao_finalizada(db_session, establishment, customer):
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    session = ChargingSession(
        user_id=customer.id,
        charger_id=charger.id,
        establishment_id=establishment.id,
        status=ChargingSessionStatus.active,
        started_at=datetime.now(_UTC),
    )
    db_session.add(session)
    db_session.commit()

    with pytest.raises(ValueError):
        build_receipt(session)
