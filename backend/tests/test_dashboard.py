from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.config import Settings
from app.models.charger import Charger, ChargerReading
from app.models.enums import ChargerModel, ChargerStatus, ChargingSessionStatus, UserRole
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.models.user import User
from app.services.dashboard import _revenue_breakdown, get_dashboard


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


def test_dashboard_revenue_today_sums_only_todays_finished_sessions(db_session, monkeypatch):
    establishment = _establishment_with_readings(db_session)
    settings = Settings()
    monkeypatch.setattr("app.services.dashboard.requests.get", _raise_connection_error)

    now = datetime.now(tz=UTC)
    charger = db_session.query(Charger).filter(Charger.establishment_id == establishment.id).one()
    customer = User(
        email="cliente-dash@teste.com",
        hashed_password="x",
        full_name="Cliente",
        role=UserRole.customer,
    )
    db_session.add(customer)
    db_session.flush()

    db_session.add_all(
        [
            ChargingSession(
                user_id=customer.id,
                charger_id=charger.id,
                establishment_id=establishment.id,
                status=ChargingSessionStatus.finished,
                started_at=now - timedelta(hours=1),
                ended_at=now - timedelta(minutes=30),
                energy_kwh=Decimal("10.000"),
                amount_due=Decimal("25.5000"),
            ),
            ChargingSession(
                user_id=customer.id,
                charger_id=charger.id,
                establishment_id=establishment.id,
                status=ChargingSessionStatus.finished,
                started_at=now - timedelta(days=2, hours=1),
                ended_at=now - timedelta(days=2),
                energy_kwh=Decimal("8.000"),
                amount_due=Decimal("100.0000"),
            ),
            ChargingSession(
                user_id=customer.id,
                charger_id=charger.id,
                establishment_id=establishment.id,
                status=ChargingSessionStatus.active,
                started_at=now - timedelta(minutes=10),
            ),
        ]
    )
    db_session.commit()

    result = get_dashboard(db_session, establishment, settings)

    assert result.revenue_today == Decimal("25.5000")
    assert result.active_sessions_count == 1


def test_revenue_breakdown_buckets_by_local_day_week_and_month(db_session):
    establishment = _establishment_with_readings(db_session)
    charger = db_session.query(Charger).filter(Charger.establishment_id == establishment.id).one()
    customer = User(
        email="cliente-receita@teste.com",
        hashed_password="x",
        full_name="Cliente",
        role=UserRole.customer,
    )
    db_session.add(customer)
    db_session.flush()

    # now_utc fixo (nao datetime.now()) pra nao depender do dia real em que o teste roda.
    # 2026-06-17 e quarta-feira: semana local comeca segunda 2026-06-15, mes comeca 2026-06-01.
    now_utc = datetime(2026, 6, 17, 18, 0, tzinfo=UTC)  # 15h local (America/Sao_Paulo, UTC-3)

    sessions = [
        (datetime(2026, 6, 17, 18, 0, tzinfo=UTC), Decimal("10.0000")),  # hoje
        (datetime(2026, 6, 15, 18, 0, tzinfo=UTC), Decimal("20.0000")),  # segunda desta semana
        (datetime(2026, 6, 1, 18, 0, tzinfo=UTC), Decimal("40.0000")),  # mes, fora da semana
        (datetime(2026, 5, 31, 18, 0, tzinfo=UTC), Decimal("80.0000")),  # mes passado
    ]
    for ended_at, amount in sessions:
        db_session.add(
            ChargingSession(
                user_id=customer.id,
                charger_id=charger.id,
                establishment_id=establishment.id,
                status=ChargingSessionStatus.finished,
                started_at=ended_at - timedelta(hours=1),
                ended_at=ended_at,
                energy_kwh=Decimal("5.000"),
                amount_due=amount,
            )
        )
    db_session.commit()

    revenue_today, revenue_week, revenue_month = _revenue_breakdown(
        db_session, establishment.id, now_utc
    )

    assert revenue_today == Decimal("10.0000")
    assert revenue_week == Decimal("30.0000")
    assert revenue_month == Decimal("70.0000")


def test_dashboard_endpoint_requires_owner(client):
    customer_token = _register_and_login(client, "cliente-dash@teste.com", "customer")
    response = client.get(
        "/establishments/00000000-0000-0000-0000-000000000000/dashboard",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 403
