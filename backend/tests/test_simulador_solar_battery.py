import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.charger import Charger, ChargerReading
from app.models.energy import EnergyAsset, SiteEnergyReading
from app.models.enums import ChargerModel, ChargerStatus, EnergyAssetKind, UserRole
from app.models.establishment import Establishment
from app.models.user import User
from app.services.energy_dispatch import BatterySpec, dispatch
from simulador.battery import SimulatedBattery
from simulador.energy_backfill import backfill
from simulador.solar import LOCAL_TZ, SolarParams, solar_power_kw

D = Decimal
PARAMS = SolarParams(peak_kwp=D("20"))


def _local(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 14, hour, minute, tzinfo=LOCAL_TZ)


def test_no_generation_at_night():
    assert solar_power_kw("INV-1", _local(3), PARAMS) == 0
    assert solar_power_kw("INV-1", _local(6), PARAMS) == 0
    assert solar_power_kw("INV-1", _local(21), PARAMS) == 0


def test_noon_is_near_peak_and_bounded_by_kwp():
    noon = solar_power_kw("INV-1", _local(12), PARAMS)
    morning = solar_power_kw("INV-1", _local(8), PARAMS)
    assert noon > morning > 0
    # teto teorico: kWp x PR x (1 + ruido maximo)
    assert noon <= D("20") * D("0.80") * D("1.05")


def test_same_instant_is_deterministic_across_timezones():
    local = _local(10, 30)
    assert solar_power_kw("INV-1", local, PARAMS) == solar_power_kw(
        "INV-1", local.astimezone(UTC), PARAMS
    )


def test_different_plants_have_different_weather():
    values = {solar_power_kw(f"INV-{i}", _local(12), PARAMS) for i in range(5)}
    assert len(values) > 1


SPEC = BatterySpec(
    capacity_kwh=D("20"),
    max_charge_kw=D("10"),
    max_discharge_kw=D("10"),
    min_soc_pct=D("10"),
    round_trip_efficiency_pct=D("90"),
)


def test_battery_discharge_stops_at_min_soc():
    battery = SimulatedBattery(SPEC, D("20"), setpoint_kw=D("10"))
    assert battery.advance(D("1")) == D("10.00")


def test_battery_charge_applies_efficiency_and_caps_at_full():
    battery = SimulatedBattery(SPEC, D("50"), setpoint_kw=D("-10"))
    assert battery.advance(D("1")) == D("95.00")
    assert battery.advance(D("1")) == D("100.00")


def test_battery_below_min_does_not_jump_up_when_discharging():
    battery = SimulatedBattery(SPEC, D("5"), setpoint_kw=D("2"))
    assert battery.advance(D("1")) == D("5.00")


def test_simulated_battery_matches_dispatch_prediction():
    """O SoC que o simulador reporta depois de aplicar o setpoint tem que bater com o que o
    despacho previu - senao o painel mostra uma bateria e a fisica faz outra."""
    dt = D("0.25")
    for load, solar, soc in [("15", "4", "60"), ("0", "12", "40"), ("3", "3", "70")]:
        result = dispatch(D(load), D(solar), SPEC, D(soc), D("40"), dt)
        battery = SimulatedBattery(SPEC, D(soc), setpoint_kw=result.battery_kw)
        assert battery.advance(dt) == result.soc_after_pct


def _backfill_fixture(db):
    owner = User(email="dono-bf@teste.com", hashed_password="x", full_name="D", role=UserRole.owner)
    db.add(owner)
    db.flush()
    establishment = Establishment(
        owner_id=owner.id,
        name="Backfill",
        kind="estacionamento",
        phase="trifasico",
        grid_connection_kw=D("75"),
        power_limit_kw=D("40"),
    )
    db.add(establishment)
    db.flush()
    charger = Charger(
        establishment_id=establishment.id,
        sems_serial=f"SN-{uuid.uuid4().hex[:6]}",
        model=ChargerModel.gw11k,
        spot_label="A",
        status=ChargerStatus.livre,
        nominal_power_kw=D("11"),
    )
    db.add(charger)
    db.add_all(
        [
            EnergyAsset(
                establishment_id=establishment.id,
                kind=EnergyAssetKind.inverter,
                sems_serial="INV-BF",
                model="inv",
                rated_kw=D("20"),
            ),
            EnergyAsset(
                establishment_id=establishment.id,
                kind=EnergyAssetKind.battery,
                sems_serial="BAT-BF",
                model="bat",
                capacity_kwh=SPEC.capacity_kwh,
                max_charge_kw=SPEC.max_charge_kw,
                max_discharge_kw=SPEC.max_discharge_kw,
                min_soc_pct=SPEC.min_soc_pct,
                round_trip_efficiency_pct=SPEC.round_trip_efficiency_pct,
            ),
        ]
    )
    db.flush()
    now = datetime.now(UTC)
    for minutes in range(0, 24 * 60, 10):
        db.add(
            ChargerReading(
                charger_id=charger.id,
                timestamp=now - timedelta(minutes=minutes),
                power_kw=D("7.400"),
                status=ChargerStatus.carregando,
                total_energy_kwh=D("0"),
            )
        )
    db.commit()
    return establishment


def test_energy_backfill_builds_balanced_rows_and_is_idempotent(db_session):
    establishment = _backfill_fixture(db_session)

    inserted = backfill(db_session, establishment, days=1, step=timedelta(minutes=5), force=False)

    # 24 h em passos de 5 min = 288 instantes (+1 porque o inicio e arredondado para baixo)
    assert inserted in (288, 289)
    rows = db_session.query(SiteEnergyReading).all()
    for row in rows:
        assert row.solar_to_load_kw + row.battery_to_load_kw + row.grid_to_load_kw == row.load_kw
        assert D("10") <= row.battery_soc_pct <= D("100")
    # 24 h sempre contem um dia claro inteiro -> houve geracao solar em algum instante
    assert any(row.solar_kw > 0 for row in rows)
    assert backfill(db_session, establishment, days=1, step=timedelta(minutes=5), force=False) == 0
