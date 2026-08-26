from decimal import Decimal

from simulador.energy import trapezoidal_energy_kwh


def test_constant_power_equals_power_times_time():
    result = trapezoidal_energy_kwh(Decimal("10.000"), Decimal("10.000"), Decimal("1"))
    assert result == Decimal("10.000")


def test_ramp_uses_average_of_the_two_powers():
    result = trapezoidal_energy_kwh(Decimal("0.000"), Decimal("10.000"), Decimal("1"))
    assert result == Decimal("5.000")


def test_zero_duration_yields_zero_energy():
    result = trapezoidal_energy_kwh(Decimal("7.400"), Decimal("7.400"), Decimal("0"))
    assert result == Decimal("0.000")


def test_result_rounded_to_three_decimal_places():
    result = trapezoidal_energy_kwh(Decimal("3.333"), Decimal("3.334"), Decimal("1"))
    assert result == Decimal("3.334")
    assert result.as_tuple().exponent == -3
