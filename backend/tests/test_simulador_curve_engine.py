import random
from decimal import Decimal

from app.models.enums import ChargerStatus
from simulador.curve_engine import RAMP_DURATION, generate_session_samples, plateau_power_kw
from simulador.vehicles import VehicleProfile

_VEHICLE = VehicleProfile(
    "Carro Teste", obc_max_kw=Decimal("7.4"), battery_capacity_kwh=Decimal("40.0")
)


def test_plateau_power_is_limited_by_the_smaller_of_charger_and_vehicle():
    assert plateau_power_kw(Decimal("22.000"), _VEHICLE) == Decimal("7.4")
    assert plateau_power_kw(Decimal("3.700"), _VEHICLE) == Decimal("3.700")


def test_plateau_samples_stay_within_the_noise_band():
    """target_soc_pct abaixo do inicio do taper (80%) isola a fase de plato: sem taper, toda
    amostra apos a rampa deve ficar dentro da banda de ruido em torno do plato."""
    rng = random.Random(1)
    samples = generate_session_samples(
        charger_nominal_kw=Decimal("22.000"),
        vehicle=_VEHICLE,
        initial_soc_pct=Decimal("0.20"),
        target_soc_pct=Decimal("0.75"),
        rng=rng,
    )
    plateau_kw = plateau_power_kw(Decimal("22.000"), _VEHICLE)
    plateau_samples = [
        s for s in samples if s.status == ChargerStatus.carregando and s.offset > RAMP_DURATION
    ]
    assert len(plateau_samples) > 1
    lower_bound = plateau_kw * Decimal("0.93")
    upper_bound = plateau_kw * Decimal("1.07")
    for sample in plateau_samples:
        assert lower_bound <= sample.power_kw <= upper_bound


def test_taper_phase_does_not_increase_power():
    rng = random.Random(2)
    samples = generate_session_samples(
        charger_nominal_kw=Decimal("11.000"),
        vehicle=_VEHICLE,
        initial_soc_pct=Decimal("0.85"),
        target_soc_pct=Decimal("1.00"),
        rng=rng,
    )
    taper_powers = [
        s.power_kw
        for s in samples
        if s.status == ChargerStatus.carregando and s.offset > RAMP_DURATION
    ]
    assert len(taper_powers) > 1
    for previous, current in zip(taper_powers, taper_powers[1:]):
        assert current <= previous * Decimal("1.05")


def test_session_ends_with_zero_power_and_livre_status():
    rng = random.Random(3)
    samples = generate_session_samples(
        charger_nominal_kw=Decimal("11.000"),
        vehicle=_VEHICLE,
        initial_soc_pct=Decimal("0.30"),
        target_soc_pct=Decimal("0.95"),
        rng=rng,
    )
    last = samples[-1]
    assert last.power_kw == Decimal("0.000")
    assert last.status == ChargerStatus.livre
