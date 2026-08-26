from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.config import Settings
from app.models.charger import Charger, ChargerReading
from app.models.enums import ChargerModel, ChargerStatus, UserRole
from app.models.establishment import Establishment
from app.models.user import User
from app.services.dashboard import get_dashboard


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


def _establishment_with_readings(db_session) -> Establishment:
    owner = User(
        email="dono-dash@teste.com", hashed_password="x", full_name="Dono", role=UserRole.owner
    )
    db_session.add(owner)
    db_session.flush()

    establishment = Establishment(
        owner_id=owner.id,
        name="Estacionamento Dashboard",
        kind="estacionamento",
        phase="trifasico",
        grid_connection_kw=Decimal("75.000"),
        power_limit_kw=Decimal("40.000"),
    )
    db_session.add(establishment)
    db_session.flush()

    charger = Charger(
        establishment_id=establishment.id,
        sems_serial="HCA-G2-DASH-001",
        model=ChargerModel.gw11k,
        spot_label="Vaga 01",
        status=ChargerStatus.carregando,
        nominal_power_kw=Decimal("11.000"),
    )
    db_session.add(charger)
    db_session.flush()

    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            ChargerReading(
                charger_id=charger.id,
                timestamp=now - timedelta(minutes=5),
                power_kw=Decimal("5.000"),
                status=ChargerStatus.carregando,
                total_energy_kwh=Decimal("10.000"),
            ),
            ChargerReading(
                charger_id=charger.id,
                timestamp=now,
                power_kw=Decimal("7.400"),
                status=ChargerStatus.carregando,
                total_energy_kwh=Decimal("10.500"),
            ),
        ]
    )
    db_session.commit()
    return establishment


def test_dashboard_aggregates_latest_reading_per_charger(db_session, monkeypatch):
    establishment = _establishment_with_readings(db_session)
    settings = Settings()
    monkeypatch.setattr(
        "app.services.dashboard.requests.get",
        _raise_connection_error,
    )

    result = get_dashboard(db_session, establishment, settings)

    assert len(result.chargers) == 1
    assert result.chargers[0].latest_power_kw == Decimal("7.400")
    assert result.total_power_kw == Decimal("7.400")
    assert result.power_pct == Decimal("0.1850")


def test_dashboard_survives_ia_being_down(db_session, monkeypatch):
    establishment = _establishment_with_readings(db_session)
    settings = Settings()
    monkeypatch.setattr("app.services.dashboard.requests.get", _raise_connection_error)

    result = get_dashboard(db_session, establishment, settings)

    assert result.ia_unavailable is True
    assert result.anomalies == []


def test_dashboard_revenue_and_sessions_are_explicitly_unavailable(db_session, monkeypatch):
    establishment = _establishment_with_readings(db_session)
    settings = Settings()
    monkeypatch.setattr(
        "app.services.dashboard.requests.get",
        _raise_connection_error,
    )

    result = get_dashboard(db_session, establishment, settings)

    assert result.revenue_today is None
    assert result.active_sessions_count is None
    assert "M3" in result.unavailable_reason


def test_dashboard_endpoint_requires_owner(client):
    customer_token = _register_and_login(client, "cliente-dash@teste.com", "customer")
    response = client.get(
        "/establishments/00000000-0000-0000-0000-000000000000/dashboard",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 403
