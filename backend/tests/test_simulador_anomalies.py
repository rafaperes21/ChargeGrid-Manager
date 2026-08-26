import random
from datetime import timedelta
from decimal import Decimal

from app.models.enums import ChargerStatus
from simulador.anomalies import (
    energy_reset_drop,
    inject_over_nominal_spike,
    inject_zero_power_stall,
)
from simulador.curve_engine import CurveSample


def _plateau_samples(power_kw: Decimal = Decimal("7.400"), count: int = 200) -> list[CurveSample]:
    return [
        CurveSample(timedelta(minutes=i), power_kw, ChargerStatus.carregando) for i in range(count)
    ]


def test_zero_power_stall_zeroes_at_least_thirty_minutes():
    samples = _plateau_samples()
    rng = random.Random(1)
    result = inject_zero_power_stall(samples, rng, min_minutes=35, max_minutes=35)

    zeroed = [
        s for s in result if s.power_kw == Decimal("0.000") and s.error_code == "ERR_ZERO_POWER"
    ]
    assert len(zeroed) >= 30


def test_over_nominal_spike_exceeds_nominal_power():
    samples = _plateau_samples()
    rng = random.Random(2)
    nominal = Decimal("7.400")
    result = inject_over_nominal_spike(
        samples, nominal, rng, factor_range=(1.2, 1.2), duration_minutes_range=(10, 10)
    )

    spiked = [s for s in result if s.error_code == "ERR_OVER_NOMINAL"]
    assert spiked
    for sample in spiked:
        assert sample.power_kw > nominal


def test_energy_reset_drop_is_strictly_lower():
    rng = random.Random(3)
    previous_total = Decimal("120.500")
    new_total = energy_reset_drop(previous_total, rng, drop_fraction_range=(0.4, 0.4))
    assert new_total < previous_total
    assert new_total == Decimal("72.300")
