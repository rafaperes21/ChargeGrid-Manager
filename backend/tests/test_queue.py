import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.charger import Charger, ChargerReading
from app.models.enums import ChargerModel, ChargerStatus, PlanKind, UserRole
from app.models.establishment import Establishment
from app.models.queue import QueueEntry
from app.models.tariff import Plan, TariffRule
from app.models.user import Subscription, User
from app.services.queue import (
    RESERVATION_TIMEOUT,
    find_active_reservation,
    get_ordered_queue,
    join_queue,
    leave_queue,
    offer_charger,
    sync_queue,
)
from app.services.sessions import start_session, sync_session


def _make_user(db, *, email: str, rfid: str | None = None) -> User:
    if rfid is None:
        rfid = f"rfid-{uuid.uuid4().hex[:8]}"
    user = User(email=email, role=UserRole.customer, full_name="Fulano", rfid_virtual_id=rfid)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_establishment(db) -> Establishment:
    owner = User(
        email=f"dono-{uuid.uuid4().hex[:6]}@teste.com", role=UserRole.owner, full_name="Dono"
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)

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


def _make_subscription_with_priority(
    db, user: User, establishment: Establishment, priority: int
) -> None:
    plan = Plan(
        establishment_id=establishment.id,
        name=f"Plano prioridade {priority}",
        kind=PlanKind.mensal,
        price=Decimal("49.90"),
        priority=priority,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    subscription = Subscription(
        user_id=user.id, plan_id=plan.id, billing_cycle_start=date.today(), active=True
    )
    db.add(subscription)
    db.commit()


@pytest.fixture
def establishment(db_session):
    return _make_establishment(db_session)


# ---------------------------------------------------------------------------
# join_queue / ordenacao
# ---------------------------------------------------------------------------


def test_join_queue_ordena_por_prioridade_depois_ordem_de_chegada(db_session, establishment):
    user_a = _make_user(db_session, email="a@teste.com")
    user_b = _make_user(db_session, email="b@teste.com")
    user_c = _make_user(db_session, email="c@teste.com")
    _make_subscription_with_priority(db_session, user_b, establishment, priority=2)

    join_queue(db_session, user_a, establishment.id)
    join_queue(db_session, user_b, establishment.id)
    join_queue(db_session, user_c, establishment.id)

    ordered = get_ordered_queue(db_session, establishment.id)
    ordered_user_ids = [entry.user_id for entry in ordered]

    assert ordered_user_ids == [user_b.id, user_a.id, user_c.id]


def test_join_queue_falha_se_usuario_ja_esta_na_fila(db_session, establishment):
    user = _make_user(db_session, email="repetido@teste.com")
    join_queue(db_session, user, establishment.id)

    with pytest.raises(HTTPException) as exc:
        join_queue(db_session, user, establishment.id)
    assert exc.value.status_code == 409


def test_join_queue_falha_se_usuario_tem_sessao_aberta(db_session, establishment):
    user = _make_user(db_session, email="ocupado@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    start_session(db_session, user, charger.id)

    with pytest.raises(HTTPException) as exc:
        join_queue(db_session, user, establishment.id)
    assert exc.value.status_code == 409


def test_leave_queue_remove_a_entrada_e_libera_reserva(db_session, establishment):
    user = _make_user(db_session, email="desiste@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    entry = join_queue(db_session, user, establishment.id)
    offer_charger(db_session, charger)

    leave_queue(db_session, entry)

    assert db_session.get(QueueEntry, entry.id) is None
    assert charger.status == ChargerStatus.livre


# ---------------------------------------------------------------------------
# offer_charger / sync_queue
# ---------------------------------------------------------------------------


def test_offer_charger_reserva_para_o_primeiro_da_fila(db_session, establishment):
    user = _make_user(db_session, email="primeiro@teste.com")
    # carregador ocupado no momento da entrada, senao join_queue ja oferece sozinho
    # (nao ha nada pra "offer_charger" testar isolado).
    charger = _make_charger(db_session, establishment, status=ChargerStatus.carregando)
    entry = join_queue(db_session, user, establishment.id)

    charger.status = ChargerStatus.livre  # sessao terminou em algum outro lugar
    db_session.commit()
    offered = offer_charger(db_session, charger)

    assert offered is not None
    assert offered.id == entry.id
    assert offered.reserved_charger_id == charger.id
    assert offered.reserved_at is not None
    assert charger.status == ChargerStatus.reservado


def test_offer_charger_pula_quem_ja_tem_oferta_ativa(db_session, establishment):
    user_a = _make_user(db_session, email="ja-reservado@teste.com")
    user_b = _make_user(db_session, email="proximo@teste.com")
    charger_a = _make_charger(db_session, establishment, status=ChargerStatus.carregando)
    charger_b = _make_charger(db_session, establishment, status=ChargerStatus.carregando)

    join_queue(db_session, user_a, establishment.id)
    entry_b = join_queue(db_session, user_b, establishment.id)

    charger_a.status = ChargerStatus.livre
    charger_b.status = ChargerStatus.livre
    db_session.commit()

    offer_charger(db_session, charger_a)  # user_a fica com oferta ativa em charger_a
    offered = offer_charger(db_session, charger_b)

    assert offered.id == entry_b.id


def test_offer_charger_nao_faz_nada_se_carregador_nao_esta_livre(db_session, establishment):
    user = _make_user(db_session, email="qualquer@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.carregando)
    join_queue(db_session, user, establishment.id)

    assert offer_charger(db_session, charger) is None


def test_sync_queue_expira_reserva_vencida_e_repassa_para_o_proximo(db_session, establishment):
    user_a = _make_user(db_session, email="expirado@teste.com")
    user_b = _make_user(db_session, email="beneficiado@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)

    entry_a = join_queue(db_session, user_a, establishment.id)
    entry_b = join_queue(db_session, user_b, establishment.id)
    offer_charger(db_session, charger)

    # forca a reserva do user_a a ter vencido ha 1 minuto
    entry_a.reserved_at = datetime.now(UTC) - RESERVATION_TIMEOUT - timedelta(minutes=1)
    db_session.commit()

    sync_queue(db_session, establishment.id)
    db_session.refresh(entry_a)
    db_session.refresh(entry_b)

    assert entry_a.reserved_charger_id is None
    assert entry_b.reserved_charger_id == charger.id
    assert charger.status == ChargerStatus.reservado

    ordered = get_ordered_queue(db_session, establishment.id)
    # user_a perdeu a vez (foi pro fim do proprio tier) mas continua na fila
    assert [e.user_id for e in ordered] == [user_b.id, user_a.id]


# ---------------------------------------------------------------------------
# integracao com services/sessions.py
# ---------------------------------------------------------------------------


def test_start_session_consome_reserva_da_fila(db_session, establishment):
    user = _make_user(db_session, email="confirma@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    entry = join_queue(db_session, user, establishment.id)
    offer_charger(db_session, charger)

    session = start_session(db_session, user, charger.id)

    assert session is not None
    assert db_session.get(QueueEntry, entry.id) is None


def test_start_session_falha_se_reserva_e_de_outro_cliente(db_session, establishment):
    user_a = _make_user(db_session, email="dono-da-reserva@teste.com")
    user_b = _make_user(db_session, email="estranho@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    join_queue(db_session, user_a, establishment.id)
    offer_charger(db_session, charger)

    with pytest.raises(HTTPException) as exc:
        start_session(db_session, user_b, charger.id)
    assert exc.value.status_code == 409


def test_sessao_finalizada_oferece_carregador_automaticamente_para_fila(db_session, establishment):
    driver = _make_user(db_session, email="motorista@teste.com")
    waiting_user = _make_user(db_session, email="esperando@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)

    tariff = TariffRule(
        establishment_id=establishment.id,
        name="Unica",
        days_of_week="0,1,2,3,4,5,6",
        start_time_local=datetime.min.time(),
        end_time_local=datetime.max.time().replace(microsecond=0),
        price_per_kwh=Decimal("2.0000"),
        is_special=False,
    )
    db_session.add(tariff)
    db_session.commit()

    started_at = datetime.now(UTC) - timedelta(minutes=10)
    session = start_session(db_session, driver, charger.id)
    session.started_at = started_at
    db_session.commit()

    # so entra na fila depois que o carregador ja esta ocupado - com ele livre,
    # join_queue ja teria oferecido na hora (nao sobraria nada pra `_release_charger` fazer).
    join_queue(db_session, waiting_user, establishment.id)

    for minutes, power in [(1, "3.000"), (2, "6.000"), (3, "0.000"), (4, "0.000")]:
        reading = ChargerReading(
            charger_id=charger.id,
            timestamp=started_at + timedelta(minutes=minutes),
            power_kw=Decimal(power),
            status=ChargerStatus.carregando if Decimal(power) > 0 else ChargerStatus.livre,
        )
        db_session.add(reading)
    db_session.commit()

    sync_session(db_session, session)

    reserved = find_active_reservation(db_session, waiting_user.id, charger.id)
    assert reserved is not None
    assert charger.status == ChargerStatus.reservado
