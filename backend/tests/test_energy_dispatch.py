from decimal import Decimal

import pytest

from app.services.energy_dispatch import (
    BatterySpec,
    dispatch,
    max_charge_kw,
    max_discharge_kw,
)

D = Decimal
ONE_MIN = D(1) / D(60)
QUARTER_H = D("0.25")


def _battery(**overrides) -> BatterySpec:
    params = {
        "capacity_kwh": D("20"),
        "max_charge_kw": D("10"),
        "max_discharge_kw": D("10"),
        "min_soc_pct": D("10"),
        "round_trip_efficiency_pct": D("90"),
    }
    params.update(overrides)
    return BatterySpec(**params)


def _assert_balanced(result):
    """Conservacao: tudo que a carga pediu foi atendido por alguma fonte ou ficou sem
    atendimento; tudo que o solar gerou foi para a carga, para a bateria ou sobrou."""
    served = result.solar_to_load_kw + result.battery_to_load_kw + result.grid_to_load_kw
    assert served + result.unserved_kw == result.load_kw
    used_solar = result.solar_to_load_kw + result.solar_to_battery_kw + result.solar_surplus_kw
    assert used_solar == result.solar_kw


def test_solar_alone_covers_load_and_surplus_charges_battery():
    result = dispatch(D("8"), D("15"), _battery(), D("50"), D("40"), ONE_MIN)
    assert result.solar_to_load_kw == D("8.000")
    assert result.battery_to_load_kw == 0
    assert result.grid_to_load_kw == 0
    assert result.solar_to_battery_kw == D("7.000")
    assert result.solar_surplus_kw == 0
    assert result.soc_after_pct > D("50")
    assert result.renewable_kw == result.load_kw
    _assert_balanced(result)


def test_solar_then_battery_before_grid():
    result = dispatch(D("20"), D("6"), _battery(), D("80"), D("40"), ONE_MIN)
    assert result.solar_to_load_kw == D("6.000")
    assert result.battery_to_load_kw == D("10.000")  # limitado pela descarga maxima
    assert result.grid_to_load_kw == D("4.000")
    assert result.battery_kw == D("10.000")  # positivo = descarregando
    assert result.soc_after_pct < D("80")
    _assert_balanced(result)


def test_night_without_battery_is_grid_only():
    result = dispatch(D("22"), D("0"), None, None, D("40"), ONE_MIN)
    assert result.grid_to_load_kw == D("22.000")
    assert result.renewable_kw == 0
    assert result.soc_after_pct is None
    _assert_balanced(result)


def test_battery_at_min_soc_does_not_discharge():
    result = dispatch(D("12"), D("0"), _battery(), D("10"), D("40"), ONE_MIN)
    assert result.battery_to_load_kw == 0
    assert result.grid_to_load_kw == D("12.000")
    assert result.soc_after_pct == D("10.00")
    _assert_balanced(result)


def test_discharge_limited_by_energy_above_min_soc():
    # 20 kWh, SoC 11% -> 0,2 kWh acima do minimo; em 15 min isso sustenta 0,8 kW
    spec = _battery()
    assert max_discharge_kw(spec, D("11"), QUARTER_H) == D("0.800")
    result = dispatch(D("5"), D("0"), spec, D("11"), D("40"), QUARTER_H)
    assert result.battery_to_load_kw == D("0.800")
    assert result.soc_after_pct == D("10.00")
    _assert_balanced(result)


def test_grid_limit_exceeded_leaves_unserved():
    result = dispatch(D("50"), D("0"), None, None, D("40"), ONE_MIN)
    assert result.grid_to_load_kw == D("40.000")
    assert result.unserved_kw == D("10.000")
    _assert_balanced(result)


def test_unlimited_grid_covers_everything():
    result = dispatch(D("50"), D("0"), None, None, None, ONE_MIN)
    assert result.grid_to_load_kw == D("50.000")
    assert result.unserved_kw == 0


def test_full_battery_sends_solar_to_surplus():
    result = dispatch(D("2"), D("12"), _battery(), D("100"), D("40"), ONE_MIN)
    assert result.solar_to_battery_kw == 0
    assert result.solar_surplus_kw == D("10.000")
    assert result.soc_after_pct == D("100.00")
    _assert_balanced(result)


def test_charge_never_overfills_battery():
    spec = _battery()
    # SoC 99% -> cabe 0,2 kWh; com 90% de eficiencia em 15 min: 0,2 / (0,25 x 0,9)
    assert max_charge_kw(spec, D("99"), QUARTER_H) == D("0.889")
    result = dispatch(D("0"), D("10"), spec, D("99"), D("40"), QUARTER_H)
    assert result.soc_after_pct <= D("100")
    _assert_balanced(result)


def test_round_trip_efficiency_applied_on_charge():
    spec = _battery()
    # 10 kW por 1 h com 90% -> 9 kWh entram: 50% (10 kWh) + 9 = 19 kWh = 95%
    result = dispatch(D("0"), D("10"), spec, D("50"), D("40"), D("1"))
    assert result.solar_to_battery_kw == D("10.000")
    assert result.soc_after_pct == D("95.00")


def test_battery_never_charges_from_grid():
    result = dispatch(D("0"), D("0"), _battery(), D("50"), D("40"), ONE_MIN)
    assert result.solar_to_battery_kw == 0
    assert result.grid_to_load_kw == 0
    assert result.soc_after_pct == D("50.00")


@pytest.mark.parametrize(
    ("load", "solar", "soc"),
    [("0", "0", "50"), ("44", "3.2", "35"), ("7.4", "18", "60"), ("39.9", "39.9", "10")],
)
def test_energy_balance_holds_across_cases(load, solar, soc):
    result = dispatch(D(load), D(solar), _battery(), D(soc), D("40"), ONE_MIN)
    _assert_balanced(result)
