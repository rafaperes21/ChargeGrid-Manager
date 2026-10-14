import asyncio
from datetime import datetime
from decimal import Decimal

from app.models.energy import EnergyAsset
from app.models.enums import BatteryDispatchMode, EnergyAssetKind
from app.models.establishment import Establishment
from app.models.user import User
from app.services.energy_assets import battery_free_discharge
from app.services.tariff_posts import LOCAL_TZ, tariff_post

D = Decimal


def _register_and_login(client, email: str, role: str) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "senha1234", "full_name": "Fulano", "role": role},
    )
    response = client.post("/auth/login", json={"email": email, "password": "senha1234"})
    return response.json()["access_token"]


def _battery(mode=BatteryDispatchMode.self_consumption, establishment_id=None):
    return EnergyAsset(
        establishment_id=establishment_id,
        kind=EnergyAssetKind.battery,
        sems_serial="BAT-MODE",
        model="Bateria (simulada)",
        capacity_kwh=D("20"),
        max_charge_kw=D("10"),
        max_discharge_kw=D("10"),
        min_soc_pct=D("10"),
        round_trip_efficiency_pct=D("90"),
        dispatch_mode=mode,
    )


def _at(hour, minute=0):
    return datetime(2026, 10, 14, hour, minute, tzinfo=LOCAL_TZ)


def test_enel_sp_posts():
    assert tariff_post(_at(17, 29)) == "intermediario"
    assert tariff_post(_at(17, 30)) == "ponta"
    assert tariff_post(_at(20, 30)) == "intermediario"
    assert tariff_post(_at(21, 30)) == "fora_ponta"


def test_free_discharge_rules():
    reserve = _battery(BatteryDispatchMode.peak_reserve)
    self_consumption = _battery(BatteryDispatchMode.self_consumption)
    assert battery_free_discharge(self_consumption, _at(10))
    assert battery_free_discharge(None, _at(10))
    assert not battery_free_discharge(reserve, _at(10))
    assert not battery_free_discharge(reserve, _at(17, 0))  # intermediario: ainda guarda
    assert battery_free_discharge(reserve, _at(18))


def _owned(client, db_session, email):
    token = _register_and_login(client, email, "owner")
    owner = db_session.query(User).filter(User.email == email).one()
    establishment = Establishment(
        owner_id=owner.id, name="Bateria", kind="estacionamento", phase="trifasico",
        grid_connection_kw=D("75"), power_limit_kw=D("40"),
    )
    db_session.add(establishment)
    db_session.commit()
    return token, establishment


def test_owner_switches_battery_mode(client, db_session):
    token, establishment = _owned(client, db_session, "dono-modo@teste.com")
    db_session.add(_battery(establishment_id=establishment.id))
    db_session.commit()

    response = client.patch(
        f"/establishments/{establishment.id}/energy/battery-mode",
        json={"dispatch_mode": "peak_reserve"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["dispatch_mode"] == "peak_reserve"
    flow = client.get(
        f"/establishments/{establishment.id}/energy/flow",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert flow["battery"]["dispatch_mode"] == "peak_reserve"


def test_battery_mode_without_battery_is_404(client, db_session):
    token, establishment = _owned(client, db_session, "dono-sem-bat@teste.com")
    response = client.patch(
        f"/establishments/{establishment.id}/energy/battery-mode",
        json={"dispatch_mode": "peak_reserve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_battery_mode_rejects_customer_and_invalid_mode(client, db_session):
    token, establishment = _owned(client, db_session, "dono-inv@teste.com")
    customer = _register_and_login(client, "cliente-modo@teste.com", "customer")
    url = f"/establishments/{establishment.id}/energy/battery-mode"
    assert client.patch(
        url, json={"dispatch_mode": "peak_reserve"},
        headers={"Authorization": f"Bearer {customer}"},
    ).status_code == 403
    assert client.patch(
        url, json={"dispatch_mode": "turbo"}, headers={"Authorization": f"Bearer {token}"}
    ).status_code == 422


def test_polling_respects_reserve_mode_outside_peak(db_session, monkeypatch):
    """Mesmo cenario do teste de polling com solar/bateria, mas em modo reserva fora da
    ponta: o solar vai para a bateria, a bateria nao descarrega e a rede cobre a carga."""
    from app.integracoes.polling import PollingService
    from app.models.energy import SiteEnergyReading
    from app.models.enums import ChargerStatus, UserRole
    from tests.test_polling import (
        _add_assets,
        _EnergyFakeSemsClient,
        _make_charger,
        _make_establishment,
        _make_user,
        _open_session,
        _reading,
    )

    monkeypatch.setattr("app.services.energy_assets.tariff_post", lambda at: "fora_ponta")
    establishment = _make_establishment(db_session, _make_user(db_session, role=UserRole.owner))
    _add_assets(db_session, establishment)
    battery = (
        db_session.query(EnergyAsset).filter(EnergyAsset.kind == EnergyAssetKind.battery).one()
    )
    battery.dispatch_mode = BatteryDispatchMode.peak_reserve
    db_session.commit()
    charger = _make_charger(db_session, establishment, status=ChargerStatus.carregando)
    _open_session(db_session, establishment, charger)
    now = datetime.now(LOCAL_TZ)
    fake = _EnergyFakeSemsClient([[_reading(charger, "11", now)]], D("3.000"), D("60.00"))

    asyncio.run(PollingService(fake).poll_once(db_session))

    site = db_session.query(SiteEnergyReading).one()
    assert site.battery_to_load_kw == 0
    assert site.solar_to_battery_kw == D("3.000")
    assert site.grid_to_load_kw == D("11.000")
