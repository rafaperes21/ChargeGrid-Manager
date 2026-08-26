import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.enums import ChargerModel, ChargerStatus
from app.models import Charger
from app.services.anomalies import (
    detect_energy_regression,
    detect_over_nominal_power,
    detect_prolonged_offline,
    detect_zero_power_while_connected,
)

_BASE_TS = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)


def _charger(nominal_kw: str = "11.000") -> Charger:
    return Charger(
        id=uuid.uuid4(),
        establishment_id=uuid.uuid4(),
        sems_serial="HCA-G2-TEST-001",
        model=ChargerModel.gw11k,
        nominal_power_kw=Decimal(nominal_kw),
        status=ChargerStatus.carregando,
    )


class _R:
    """Leitura minima, so com os campos que as regras precisam - evita depender de uma
    sessao de banco para montar `ChargerReading` completo."""

    def __init__(self, offset_minutes, power_kw, status, total_energy_kwh="0.000", error_code=None):
        self.timestamp = _BASE_TS + timedelta(minutes=offset_minutes)
        self.power_kw = Decimal(str(power_kw))
        self.status = status
        self.total_energy_kwh = Decimal(str(total_energy_kwh))
        self.error_code = error_code


def test_zero_power_alerts_when_stall_exceeds_threshold():
    charger = _charger()
    readings = [_R(i, "0.000", ChargerStatus.carregando) for i in range(0, 36)]
    alerts = detect_zero_power_while_connected(charger, readings, min_minutes=30)
    assert len(alerts) == 1
    assert alerts[0].rule == "zero_power_connected"
    assert alerts[0].severity == "high"


def test_zero_power_does_not_alert_below_threshold():
    charger = _charger()
    readings = [_R(i, "0.000", ChargerStatus.carregando) for i in range(0, 20)]
    assert detect_zero_power_while_connected(charger, readings, min_minutes=30) == []


def test_over_nominal_power_alerts_above_tolerance():
    charger = _charger(nominal_kw="7.400")
    readings = [_R(0, "7.400", ChargerStatus.carregando), _R(1, "9.500", ChargerStatus.carregando)]
    alerts = detect_over_nominal_power(charger, readings, tolerance_pct=Decimal("0.05"))
    assert len(alerts) == 1
    assert alerts[0].rule == "over_nominal_power"


def test_over_nominal_power_tolerates_small_measurement_noise():
    charger = _charger(nominal_kw="7.400")
    readings = [_R(0, "7.400", ChargerStatus.carregando), _R(1, "7.550", ChargerStatus.carregando)]
    assert detect_over_nominal_power(charger, readings, tolerance_pct=Decimal("0.05")) == []


def test_prolonged_offline_flags_a_gap_without_readings():
    charger = _charger()
    readings = [_R(0, "0.000", ChargerStatus.livre), _R(50, "0.000", ChargerStatus.livre)]
    alerts = detect_prolonged_offline(charger, readings, cycles=3, cycle_minutes=15)
    assert len(alerts) == 1
    assert alerts[0].rule == "offline_prolonged"


def test_prolonged_offline_ignores_a_small_gap():
    charger = _charger()
    readings = [_R(0, "0.000", ChargerStatus.livre), _R(20, "0.000", ChargerStatus.livre)]
    assert detect_prolonged_offline(charger, readings, cycles=3, cycle_minutes=15) == []


def test_energy_regression_detects_exactly_one_drop():
    charger = _charger()
    readings = [
        _R(0, "0.000", ChargerStatus.carregando, total_energy_kwh="10.000"),
        _R(1, "7.000", ChargerStatus.carregando, total_energy_kwh="12.000"),
        _R(2, "7.000", ChargerStatus.carregando, total_energy_kwh="11.000"),
        _R(3, "7.000", ChargerStatus.carregando, total_energy_kwh="13.000"),
    ]
    alerts = detect_energy_regression(charger, readings)
    assert len(alerts) == 1
    assert alerts[0].rule == "energy_regression"
    assert alerts[0].window_start == readings[1].timestamp
    assert alerts[0].window_end == readings[2].timestamp
