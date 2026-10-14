import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.models.energy import EnergyAsset, SiteEnergyReading
from app.models.enums import EnergyAssetKind
from app.models.establishment import Establishment
from app.models.user import User
from app.services.energy_flow import LOCAL_TZ, summarize

D = Decimal


def _register_and_login(client, email: str, role: str) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "senha1234", "full_name": "Fulano", "role": role},
    )
    response = client.post("/auth/login", json={"email": email, "password": "senha1234"})
    return response.json()["access_token"]


def _reading(establishment_id, ts, *, load, solar, battery_to_load="0", grid=None, soc="50"):
    load, solar, battery_to_load = D(load), D(solar), D(battery_to_load)
    solar_to_load = min(load, solar)
    grid = D(grid) if grid is not None else load - solar_to_load - battery_to_load
    return SiteEnergyReading(
        establishment_id=establishment_id,
        timestamp=ts,
        load_kw=load,
        solar_kw=solar,
        solar_to_load_kw=solar_to_load,
        battery_to_load_kw=battery_to_load,
        grid_to_load_kw=grid,
        solar_to_battery_kw=D("0"),
        solar_surplus_kw=solar - solar_to_load,
        battery_kw=battery_to_load,
        battery_soc_pct=D(soc),
        grid_limit_kw=D("40"),
        demand_limited_kw=D("0"),
    )


def test_summarize_integrates_by_trapezoid_and_skips_gaps():
    est_id = uuid.uuid4()
    t0 = datetime(2026, 10, 14, 15, 0, tzinfo=UTC)
    readings = [
        _reading(est_id, t0, load="10", solar="10"),
        _reading(est_id, t0 + timedelta(minutes=6), load="10", solar="10"),
        # buraco de 1 h (polling fora do ar) - nao pode virar energia
        _reading(est_id, t0 + timedelta(minutes=66), load="10", solar="0"),
        _reading(est_id, t0 + timedelta(minutes=72), load="10", solar="0"),
    ]
    summary = summarize(readings, date(2026, 10, 14), date(2026, 10, 14))
    # 2 intervalos de 6 min x 10 kW = 2 kWh de carga; 1 kWh solar e 1 kWh rede
    assert summary.load_kwh == D("2.000")
    assert summary.solar_to_load_kwh == D("1.000")
    assert summary.grid_to_load_kwh == D("1.000")
    assert summary.renewable_share_pct == D("50.0")
    assert summary.readings_count == 4


def test_summarize_without_load_has_no_share():
    summary = summarize([], date(2026, 10, 14), date(2026, 10, 14))
    assert summary.renewable_share_pct is None
    assert summary.load_kwh == 0


def _owned_establishment(client, db_session, email="dono-energia@teste.com"):
    token = _register_and_login(client, email, "owner")
    owner = db_session.query(User).filter(User.email == email).one()
    establishment = Establishment(
        owner_id=owner.id,
        name="Estacionamento Solar",
        kind="estacionamento",
        phase="trifasico",
        grid_connection_kw=D("75"),
        power_limit_kw=D("40"),
    )
    db_session.add(establishment)
    db_session.commit()
    return token, establishment


def test_flow_endpoint_returns_assets_latest_series_and_today(client, db_session):
    token, establishment = _owned_establishment(client, db_session)
    db_session.add(
        EnergyAsset(
            establishment_id=establishment.id,
            kind=EnergyAssetKind.battery,
            sems_serial="BAT-API-1",
            model="Bateria (simulada)",
            capacity_kwh=D("20"),
            max_charge_kw=D("10"),
            max_discharge_kw=D("10"),
            min_soc_pct=D("10"),
            round_trip_efficiency_pct=D("90"),
        )
    )
    now = datetime.now(UTC)
    for minutes in (2, 1, 0):
        db_session.add(
            _reading(establishment.id, now - timedelta(minutes=minutes), load="20", solar="5",
                     battery_to_load="5")
        )
    db_session.commit()

    response = client.get(
        f"/establishments/{establishment.id}/energy/flow",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["inverter"] is None
    assert body["battery"]["sems_serial"] == "BAT-API-1"
    assert D(body["latest"]["grid_to_load_kw"]) == D("10")
    assert len(body["series"]) >= 1
    # leituras de hoje (horario local) entram no resumo do dia
    if now.astimezone(LOCAL_TZ).date() == (now - timedelta(minutes=2)).astimezone(LOCAL_TZ).date():
        assert D(body["today"]["renewable_share_pct"]) == D("50.0")


def test_flow_endpoint_without_readings_is_empty_not_error(client, db_session):
    token, establishment = _owned_establishment(client, db_session)
    response = client.get(
        f"/establishments/{establishment.id}/energy/flow",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["latest"] is None
    assert response.json()["series"] == []


def test_flow_endpoint_forbids_customer(client, db_session):
    _, establishment = _owned_establishment(client, db_session)
    customer_token = _register_and_login(client, "cliente-energia@teste.com", "customer")
    response = client.get(
        f"/establishments/{establishment.id}/energy/flow",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 403


def test_flow_endpoint_unknown_establishment_is_404(client, db_session):
    token, _ = _owned_establishment(client, db_session)
    response = client.get(
        f"/establishments/{uuid.uuid4()}/energy/flow",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_summary_endpoint_rejects_inverted_period(client, db_session):
    token, establishment = _owned_establishment(client, db_session)
    response = client.get(
        f"/establishments/{establishment.id}/energy/summary",
        params={"from": "2026-10-10", "to": "2026-10-01"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
