from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.config import Settings
from app.models.charger import Charger, ChargerReading
from app.models.enums import ChargerModel, ChargerStatus, ChargingSessionStatus, UserRole
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.models.user import User
from app.services.charger_detail import get_charger_detail, uptime_pct


def _raise_connection_error(*args, **kwargs):
    import requests

    raise requests.ConnectionError("ia indisponivel neste teste")


def _register_and_login(client, email: str, role: str) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "senha1234", "full_name": "Fulano", "role": role},
    )
    response = client.post("/auth/login", json={"email": email, "password": "senha1234"})
    return response.json()["access_token"]


def _establishment_with_two_chargers(db_session) -> tuple[Establishment, Charger, Charger]:
    owner = User(
        email="dono-detalhe@teste.com", hashed_password="x", full_name="Dono", role=UserRole.owner
    )
    db_session.add(owner)
    db_session.flush()

    establishment = Establishment(
        owner_id=owner.id,
        name="Estacionamento Detalhe",
        kind="estacionamento",
        phase="trifasico",
        grid_connection_kw=Decimal("75.000"),
        power_limit_kw=Decimal("40.000"),
    )
    db_session.add(establishment)
    db_session.flush()

    charger_a = Charger(
        establishment_id=establishment.id,
        sems_serial="HCA-G2-DET-001",
        model=ChargerModel.gw11k,
        spot_label="Vaga 01",
        status=ChargerStatus.carregando,
        nominal_power_kw=Decimal("11.000"),
    )
    charger_b = Charger(
        establishment_id=establishment.id,
        sems_serial="HCA-G2-DET-002",
        model=ChargerModel.gw11k,
        spot_label="Vaga 02",
        status=ChargerStatus.livre,
        nominal_power_kw=Decimal("11.000"),
    )
    db_session.add_all([charger_a, charger_b])
    db_session.commit()
    return establishment, charger_a, charger_b


def test_uptime_pct_is_none_without_any_reading():
    assert uptime_pct([]) is None


def test_uptime_pct_computes_fraction_online():
    now = datetime.now(tz=UTC)
    readings = [
        ChargerReading(
            charger_id=None, timestamp=now, power_kw=Decimal("5"), status=ChargerStatus.carregando
        ),
        ChargerReading(
            charger_id=None, timestamp=now, power_kw=Decimal("0"), status=ChargerStatus.livre
        ),
        ChargerReading(
            charger_id=None, timestamp=now, power_kw=Decimal("0"), status=ChargerStatus.offline
        ),
        ChargerReading(
            charger_id=None, timestamp=now, power_kw=Decimal("0"), status=ChargerStatus.offline
        ),
    ]
    assert uptime_pct(readings) == Decimal("0.5000")


def test_get_charger_detail_excludes_readings_outside_window_but_keeps_true_latest(
    db_session, monkeypatch
):
    establishment, charger_a, _charger_b = _establishment_with_two_chargers(db_session)
    monkeypatch.setattr("app.services.dashboard.requests.get", _raise_connection_error)
    now = datetime.now(tz=UTC)

    db_session.add_all(
        [
            ChargerReading(
                charger_id=charger_a.id,
                timestamp=now - timedelta(hours=48),
                power_kw=Decimal("3.000"),
                status=ChargerStatus.carregando,
            ),
            ChargerReading(
                charger_id=charger_a.id,
                timestamp=now - timedelta(hours=1),
                power_kw=Decimal("7.400"),
                status=ChargerStatus.carregando,
            ),
        ]
    )
    db_session.commit()

    result = get_charger_detail(db_session, charger_a, Settings(), hours=24)

    assert len(result.power_readings) == 1
    assert result.power_readings[0].power_kw == Decimal("7.400")
    # latest_power_kw nao e restrito a janela - usa a leitura mais recente de sempre.
    assert result.latest_power_kw == Decimal("7.400")
    assert result.uptime_pct == Decimal("1.0000")


def test_get_charger_detail_has_no_data_is_none_not_zero(db_session, monkeypatch):
    establishment, charger_a, _charger_b = _establishment_with_two_chargers(db_session)
    monkeypatch.setattr("app.services.dashboard.requests.get", _raise_connection_error)

    result = get_charger_detail(db_session, charger_a, Settings(), hours=24)

    assert result.uptime_pct is None
    assert result.power_readings == []
    assert result.latest_power_kw is None


def test_get_charger_detail_sessions_scoped_to_this_charger_only(db_session, monkeypatch):
    establishment, charger_a, charger_b = _establishment_with_two_chargers(db_session)
    monkeypatch.setattr("app.services.dashboard.requests.get", _raise_connection_error)
    customer = User(
        email="cliente-detalhe@teste.com",
        hashed_password="x",
        full_name="Cliente",
        role=UserRole.customer,
    )
    db_session.add(customer)
    db_session.flush()
    now = datetime.now(tz=UTC)

    db_session.add_all(
        [
            ChargingSession(
                user_id=customer.id,
                charger_id=charger_a.id,
                establishment_id=establishment.id,
                status=ChargingSessionStatus.finished,
                started_at=now - timedelta(hours=1),
                ended_at=now - timedelta(minutes=30),
                energy_kwh=Decimal("10.000"),
                amount_due=Decimal("25.5000"),
            ),
            ChargingSession(
                user_id=customer.id,
                charger_id=charger_b.id,
                establishment_id=establishment.id,
                status=ChargingSessionStatus.finished,
                started_at=now - timedelta(hours=2),
                ended_at=now - timedelta(hours=1, minutes=30),
                energy_kwh=Decimal("5.000"),
                amount_due=Decimal("12.0000"),
            ),
        ]
    )
    db_session.commit()

    result = get_charger_detail(db_session, charger_a, Settings(), hours=24)

    assert len(result.recent_sessions) == 1
    assert result.recent_sessions[0].charger_id == charger_a.id


def test_charger_detail_endpoint_requires_owner(client):
    customer_token = _register_and_login(client, "cliente-detalhe-ep@teste.com", "customer")
    response = client.get(
        "/chargers/00000000-0000-0000-0000-000000000000/detail",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 403


def test_charger_detail_endpoint_404_for_charger_owned_by_someone_else(client, db_session):
    establishment, charger_a, _charger_b = _establishment_with_two_chargers(db_session)
    other_owner_token = _register_and_login(client, "outro-dono@teste.com", "owner")

    response = client.get(
        f"/chargers/{charger_a.id}/detail",
        headers={"Authorization": f"Bearer {other_owner_token}"},
    )
    assert response.status_code == 404
