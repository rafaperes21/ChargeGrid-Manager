import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.charger import Charger
from app.models.enums import ChargerModel, ChargerStatus, ReservationStatus, UserRole
from app.models.establishment import Establishment
from app.models.reservation import Reservation
from app.models.user import User
from app.services.reservations import (
    NO_SHOW_TOLERANCE,
    cancel_reservation,
    create_reservation,
    find_active_reservation,
    get_establishment_reservations,
    get_my_reservations,
    sync_reservations,
)
from app.services.sessions import start_session


def _make_user(db, *, email: str) -> User:
    user = User(
        email=email,
        role=UserRole.customer,
        full_name="Fulano",
        rfid_virtual_id=f"rfid-{uuid.uuid4().hex[:8]}",
    )
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


@pytest.fixture
def establishment(db_session):
    return _make_establishment(db_session)


# ---------------------------------------------------------------------------
# create_reservation
# ---------------------------------------------------------------------------


def test_create_reservation_com_sucesso(db_session, establishment):
    user = _make_user(db_session, email="reserva@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    start = datetime.now(UTC) + timedelta(hours=2)

    reservation = create_reservation(
        db_session, user, charger.id, start, start + timedelta(hours=1)
    )

    assert reservation.status == ReservationStatus.pending
    assert reservation.charger_id == charger.id
    assert reservation.user_id == user.id


def test_create_reservation_falha_se_horario_de_inicio_no_passado(db_session, establishment):
    user = _make_user(db_session, email="passado@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    start = datetime.now(UTC) - timedelta(hours=1)

    with pytest.raises(HTTPException) as exc:
        create_reservation(db_session, user, charger.id, start, start + timedelta(hours=1))
    assert exc.value.status_code == 400


def test_create_reservation_falha_se_fim_antes_do_inicio(db_session, establishment):
    user = _make_user(db_session, email="invertido@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    start = datetime.now(UTC) + timedelta(hours=2)

    with pytest.raises(HTTPException) as exc:
        create_reservation(db_session, user, charger.id, start, start - timedelta(minutes=30))
    assert exc.value.status_code == 400


def test_create_reservation_falha_se_sobrepoe_reserva_existente_do_mesmo_carregador(
    db_session, establishment
):
    user_a = _make_user(db_session, email="primeiro-reserva@teste.com")
    user_b = _make_user(db_session, email="segundo-reserva@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    start = datetime.now(UTC) + timedelta(hours=2)
    create_reservation(db_session, user_a, charger.id, start, start + timedelta(hours=1))

    # sobreposicao parcial: comeca 30 min antes do fim da primeira reserva
    overlapping_start = start + timedelta(minutes=30)
    with pytest.raises(HTTPException) as exc:
        create_reservation(
            db_session,
            user_b,
            charger.id,
            overlapping_start,
            overlapping_start + timedelta(hours=1),
        )
    assert exc.value.status_code == 409


def test_create_reservation_permite_horarios_nao_sobrepostos(db_session, establishment):
    user = _make_user(db_session, email="sem-sobreposicao@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    start = datetime.now(UTC) + timedelta(hours=2)
    create_reservation(db_session, user, charger.id, start, start + timedelta(hours=1))

    # comeca exatamente quando a primeira termina - nao ha sobreposicao
    second = create_reservation(
        db_session, user, charger.id, start + timedelta(hours=1), start + timedelta(hours=2)
    )
    assert second.status == ReservationStatus.pending


def test_create_reservation_falha_para_carregador_inexistente(db_session):
    user = _make_user(db_session, email="carregador-fantasma@teste.com")
    start = datetime.now(UTC) + timedelta(hours=2)

    with pytest.raises(HTTPException) as exc:
        create_reservation(db_session, user, uuid.uuid4(), start, start + timedelta(hours=1))
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# sync_reservations
# ---------------------------------------------------------------------------


def test_sync_reservations_ocupa_vaga_no_horario_agendado(db_session, establishment):
    user = _make_user(db_session, email="na-hora@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    reservation = Reservation(
        user_id=user.id,
        charger_id=charger.id,
        scheduled_start=datetime.now(UTC) - timedelta(minutes=1),
        scheduled_end=datetime.now(UTC) + timedelta(minutes=59),
        status=ReservationStatus.pending,
    )
    db_session.add(reservation)
    db_session.commit()

    sync_reservations(db_session, establishment.id)
    db_session.refresh(charger)
    db_session.refresh(reservation)

    assert charger.status == ChargerStatus.reservado
    assert reservation.status == ReservationStatus.pending


def test_sync_reservations_marca_no_show_apos_tolerancia_e_libera_vaga(db_session, establishment):
    user = _make_user(db_session, email="no-show@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    reservation = Reservation(
        user_id=user.id,
        charger_id=charger.id,
        scheduled_start=datetime.now(UTC) - NO_SHOW_TOLERANCE - timedelta(minutes=1),
        scheduled_end=datetime.now(UTC) + timedelta(minutes=30),
        status=ReservationStatus.pending,
    )
    db_session.add(reservation)
    db_session.commit()

    sync_reservations(db_session, establishment.id)
    db_session.refresh(charger)
    db_session.refresh(reservation)

    assert reservation.status == ReservationStatus.no_show
    assert charger.status == ChargerStatus.livre


def test_sync_reservations_nao_mexe_em_reserva_futura(db_session, establishment):
    user = _make_user(db_session, email="futuro@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    reservation = Reservation(
        user_id=user.id,
        charger_id=charger.id,
        scheduled_start=datetime.now(UTC) + timedelta(hours=3),
        scheduled_end=datetime.now(UTC) + timedelta(hours=4),
        status=ReservationStatus.pending,
    )
    db_session.add(reservation)
    db_session.commit()

    sync_reservations(db_session, establishment.id)
    db_session.refresh(charger)

    assert charger.status == ChargerStatus.livre


# ---------------------------------------------------------------------------
# cancel_reservation / consume_reservation
# ---------------------------------------------------------------------------


def test_cancel_reservation_libera_vaga_reservada(db_session, establishment):
    user = _make_user(db_session, email="cancela@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    now = datetime.now(UTC)
    reservation = create_reservation(
        db_session, user, charger.id, now + timedelta(hours=1), now + timedelta(hours=2)
    )
    charger.status = ChargerStatus.reservado  # simula sync_reservations ja ter ocupado
    db_session.commit()

    cancel_reservation(db_session, reservation)
    db_session.refresh(charger)

    assert reservation.status == ReservationStatus.cancelled
    assert charger.status == ChargerStatus.livre


def test_cancel_reservation_falha_se_ja_nao_esta_pending(db_session, establishment):
    user = _make_user(db_session, email="ja-cancelada@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    now = datetime.now(UTC)
    reservation = create_reservation(
        db_session, user, charger.id, now + timedelta(hours=1), now + timedelta(hours=2)
    )
    cancel_reservation(db_session, reservation)

    with pytest.raises(HTTPException) as exc:
        cancel_reservation(db_session, reservation)
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# integracao com services/sessions.py
# ---------------------------------------------------------------------------


def test_start_session_consome_reserva_antecipada_dentro_da_janela(db_session, establishment):
    user = _make_user(db_session, email="chegou-na-hora@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    reservation = Reservation(
        user_id=user.id,
        charger_id=charger.id,
        scheduled_start=datetime.now(UTC) - timedelta(minutes=1),
        scheduled_end=datetime.now(UTC) + timedelta(minutes=59),
        status=ReservationStatus.pending,
    )
    db_session.add(reservation)
    db_session.commit()
    sync_reservations(db_session, establishment.id)  # ocupa a vaga, como o polling real faria

    session = start_session(db_session, user, charger.id)

    db_session.refresh(reservation)
    assert session is not None
    assert reservation.status == ReservationStatus.fulfilled


def test_start_session_falha_se_reserva_antecipada_e_de_outro_cliente(db_session, establishment):
    user_a = _make_user(db_session, email="reservou@teste.com")
    user_b = _make_user(db_session, email="chegou-sem-reserva@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    reservation = Reservation(
        user_id=user_a.id,
        charger_id=charger.id,
        scheduled_start=datetime.now(UTC) - timedelta(minutes=1),
        scheduled_end=datetime.now(UTC) + timedelta(minutes=59),
        status=ReservationStatus.pending,
    )
    db_session.add(reservation)
    db_session.commit()
    sync_reservations(db_session, establishment.id)

    with pytest.raises(HTTPException) as exc:
        start_session(db_session, user_b, charger.id)
    assert exc.value.status_code == 409


def test_find_active_reservation_none_apos_expirar_tolerancia(db_session, establishment):
    user = _make_user(db_session, email="expirou@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    reservation = Reservation(
        user_id=user.id,
        charger_id=charger.id,
        scheduled_start=datetime.now(UTC) - NO_SHOW_TOLERANCE - timedelta(minutes=1),
        scheduled_end=datetime.now(UTC) + timedelta(minutes=30),
        status=ReservationStatus.pending,
    )
    db_session.add(reservation)
    db_session.commit()

    assert find_active_reservation(db_session, user.id, charger.id) is None


# ---------------------------------------------------------------------------
# listagens
# ---------------------------------------------------------------------------


def test_get_my_reservations_ordena_do_mais_recente_para_o_mais_antigo(db_session, establishment):
    user = _make_user(db_session, email="minhas-reservas@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.livre)
    now = datetime.now(UTC)
    earlier = create_reservation(
        db_session, user, charger.id, now + timedelta(hours=1), now + timedelta(hours=2)
    )
    later = create_reservation(
        db_session, user, charger.id, now + timedelta(hours=3), now + timedelta(hours=4)
    )

    reservations = get_my_reservations(db_session, user.id)

    assert [r.id for r in reservations] == [later.id, earlier.id]


def test_get_establishment_reservations_sincroniza_antes_de_listar(db_session, establishment):
    user = _make_user(db_session, email="agenda-dono@teste.com")
    charger = _make_charger(db_session, establishment, status=ChargerStatus.reservado)
    reservation = Reservation(
        user_id=user.id,
        charger_id=charger.id,
        scheduled_start=datetime.now(UTC) - NO_SHOW_TOLERANCE - timedelta(minutes=1),
        scheduled_end=datetime.now(UTC) + timedelta(minutes=30),
        status=ReservationStatus.pending,
    )
    db_session.add(reservation)
    db_session.commit()

    reservations = get_establishment_reservations(db_session, establishment.id)

    assert reservations[0].status == ReservationStatus.no_show
