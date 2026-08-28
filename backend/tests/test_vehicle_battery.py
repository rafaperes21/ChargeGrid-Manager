from decimal import Decimal

from app.services.vehicle_battery import estimate_battery_status


def test_estimate_battery_status_unknown_model_returns_none():
    pct, minutes = estimate_battery_status(
        vehicle_model="Carro Desconhecido",
        energy_kwh=Decimal("10.000"),
        current_power_kw=Decimal("7.000"),
    )
    assert pct is None
    assert minutes is None


def test_estimate_battery_status_no_model_returns_none():
    pct, minutes = estimate_battery_status(
        vehicle_model=None, energy_kwh=Decimal("10.000"), current_power_kw=Decimal("7.000")
    )
    assert pct is None
    assert minutes is None


def test_estimate_battery_status_computes_pct_and_remaining_minutes():
    # Volvo EX30 = 51.000 kWh no catalogo.
    pct, minutes = estimate_battery_status(
        vehicle_model="Volvo EX30",
        energy_kwh=Decimal("6.000"),
        current_power_kw=Decimal("6.000"),
    )
    assert pct == Decimal("11.8")
    assert minutes == 450


def test_estimate_battery_status_caps_pct_at_100_when_energy_exceeds_capacity():
    pct, _minutes = estimate_battery_status(
        vehicle_model="Renault Kwid E-Tech",
        energy_kwh=Decimal("40.000"),
        current_power_kw=Decimal("5.000"),
    )
    assert pct == Decimal("100.0")


def test_estimate_battery_status_no_remaining_minutes_without_current_power():
    pct, minutes = estimate_battery_status(
        vehicle_model="Volvo EX30",
        energy_kwh=Decimal("6.000"),
        current_power_kw=None,
    )
    assert pct == Decimal("11.8")
    assert minutes is None


def test_estimate_battery_status_no_remaining_minutes_when_power_is_zero():
    pct, minutes = estimate_battery_status(
        vehicle_model="Volvo EX30",
        energy_kwh=Decimal("6.000"),
        current_power_kw=Decimal("0.000"),
    )
    assert pct == Decimal("11.8")
    assert minutes is None
