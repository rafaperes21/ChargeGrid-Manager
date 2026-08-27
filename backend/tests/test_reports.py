from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.charger import Charger
from app.models.enums import ChargerModel, ChargerStatus, ChargingSessionStatus, UserRole
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.models.user import User
from app.services.reports import get_charger_occupancy, get_report


def _register_and_login(client, email: str, role: str) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "senha1234", "full_name": "Fulano", "role": role},
    )
    response = client.post("/auth/login", json={"email": email, "password": "senha1234"})
    return response.json()["access_token"]


def _setup(db_session) -> tuple[Establishment, Charger, User]:
    owner = User(
        email="dono-rel@teste.com", hashed_password="x", full_name="Dono", role=UserRole.owner
    )
    db_session.add(owner)
    db_session.flush()

    establishment = Establishment(
        owner_id=owner.id,
        name="Estacionamento Relatorio",
        kind="estacionamento",
        phase="trifasico",
        grid_connection_kw=Decimal("75.000"),
        power_limit_kw=Decimal("40.000"),
    )
    db_session.add(establishment)
    db_session.flush()

    charger = Charger(
        establishment_id=establishment.id,
        sems_serial="HCA-G2-REL-001",
        model=ChargerModel.gw11k,
        spot_label="Vaga 01",
        status=ChargerStatus.livre,
        nominal_power_kw=Decimal("11.000"),
    )
    db_session.add(charger)
    db_session.flush()

    customer = User(
        email="cliente-rel@teste.com",
        hashed_password="x",
        full_name="Cliente",
        role=UserRole.customer,
    )
    db_session.add(customer)
    db_session.commit()

    return establishment, charger, customer


def _finished_session(establishment, charger, customer, ended_at, amount_due, energy_kwh):
    return ChargingSession(
        user_id=customer.id,
        charger_id=charger.id,
        establishment_id=establishment.id,
        status=ChargingSessionStatus.finished,
        started_at=ended_at,
        ended_at=ended_at,
        energy_kwh=energy_kwh,
        amount_due=amount_due,
    )


def test_get_report_aggregates_only_sessions_within_period(db_session):
    establishment, charger, customer = _setup(db_session)

    db_session.add_all(
        [
            _finished_session(
                establishment, charger, customer,
                datetime(2026, 6, 10, 18, 0, tzinfo=UTC), Decimal("10.0000"), Decimal("5.000"),
            ),
            _finished_session(
                establishment, charger, customer,
                datetime(2026, 6, 15, 18, 0, tzinfo=UTC), Decimal("20.0000"), Decimal("8.000"),
            ),
            _finished_session(
                establishment, charger, customer,
                datetime(2026, 7, 1, 18, 0, tzinfo=UTC), Decimal("999.0000"), Decimal("50.000"),
            ),
        ]
    )
    db_session.commit()

    report = get_report(db_session, establishment.id, date(2026, 6, 1), date(2026, 6, 30))

    assert report.completed_sessions_count == 2
    assert report.revenue_total == Decimal("30.0000")
    assert report.total_energy_kwh == Decimal("13.000")
    assert report.average_ticket == Decimal("15.0000")
    assert len(report.daily_revenue) == 2


def test_get_report_average_ticket_none_when_no_sessions(db_session):
    establishment, _, _ = _setup(db_session)
    report = get_report(db_session, establishment.id, date(2026, 6, 1), date(2026, 6, 30))
    assert report.completed_sessions_count == 0
    assert report.average_ticket is None
    assert report.revenue_total == Decimal("0.0000")


def test_reports_endpoint_requires_owner(client):
    customer_token = _register_and_login(client, "cliente-rel-api@teste.com", "customer")
    response = client.get(
        "/establishments/00000000-0000-0000-0000-000000000000/reports",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 403


def test_reports_endpoint_rejects_inverted_range(client):
    owner_token = _register_and_login(client, "dono-rel-api@teste.com", "owner")
    establishment_id = client.post(
        "/establishments",
        json={
            "name": "Estacionamento API",
            "kind": "estacionamento",
            "phase": "trifasico",
            "grid_connection_kw": "75.000",
            "power_limit_kw": "40.000",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["id"]

    response = client.get(
        f"/establishments/{establishment_id}/reports?from=2026-06-30&to=2026-06-01",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 400


def _timed_session(establishment, charger, customer, started_at, ended_at, amount_due, energy_kwh):
    return ChargingSession(
        user_id=customer.id,
        charger_id=charger.id,
        establishment_id=establishment.id,
        status=ChargingSessionStatus.finished,
        started_at=started_at,
        ended_at=ended_at,
        energy_kwh=energy_kwh,
        amount_due=amount_due,
    )


def test_get_charger_occupancy_scopes_totals_per_charger_and_period(db_session):
    establishment, charger_a, customer = _setup(db_session)
    charger_b = Charger(
        establishment_id=establishment.id,
        sems_serial="HCA-G2-REL-002",
        model=ChargerModel.gw11k,
        spot_label="Vaga 02",
        status=ChargerStatus.livre,
        nominal_power_kw=Decimal("11.000"),
    )
    db_session.add(charger_b)
    db_session.commit()

    db_session.add_all(
        [
            _timed_session(
                establishment, charger_a, customer,
                datetime(2026, 6, 10, 18, 0, tzinfo=UTC), datetime(2026, 6, 10, 20, 0, tzinfo=UTC),
                Decimal("10.0000"), Decimal("5.000"),
            ),
            _timed_session(
                establishment, charger_a, customer,
                datetime(2026, 6, 12, 18, 0, tzinfo=UTC), datetime(2026, 6, 12, 19, 30, tzinfo=UTC),
                Decimal("8.0000"), Decimal("4.000"),
            ),
            _timed_session(
                establishment, charger_b, customer,
                datetime(2026, 6, 11, 18, 0, tzinfo=UTC), datetime(2026, 6, 11, 19, 0, tzinfo=UTC),
                Decimal("6.0000"), Decimal("3.000"),
            ),
            # fora do periodo pedido - nao pode contar.
            _timed_session(
                establishment, charger_a, customer,
                datetime(2026, 7, 1, 18, 0, tzinfo=UTC), datetime(2026, 7, 1, 19, 0, tzinfo=UTC),
                Decimal("999.0000"), Decimal("50.000"),
            ),
        ]
    )
    db_session.commit()

    result = get_charger_occupancy(
        db_session, establishment.id, date(2026, 6, 1), date(2026, 6, 30)
    )

    by_label = {row.spot_label: row for row in result.chargers}
    assert by_label["Vaga 01"].sessions_count == 2
    assert by_label["Vaga 01"].revenue == Decimal("18.0000")
    assert by_label["Vaga 01"].energy_kwh == Decimal("9.000")
    assert by_label["Vaga 01"].hours_charged == Decimal("3.50")
    assert by_label["Vaga 02"].sessions_count == 1
    assert by_label["Vaga 02"].revenue == Decimal("6.0000")


def test_get_charger_occupancy_includes_chargers_with_no_sessions(db_session):
    establishment, charger, _customer = _setup(db_session)
    result = get_charger_occupancy(
        db_session, establishment.id, date(2026, 6, 1), date(2026, 6, 30)
    )
    assert len(result.chargers) == 1
    assert result.chargers[0].charger_id == charger.id
    assert result.chargers[0].sessions_count == 0
    assert result.chargers[0].revenue == Decimal("0.0000")


def test_charger_occupancy_endpoint_requires_owner(client):
    customer_token = _register_and_login(client, "cliente-occ-api@teste.com", "customer")
    response = client.get(
        "/establishments/00000000-0000-0000-0000-000000000000/chargers-occupancy",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 403
