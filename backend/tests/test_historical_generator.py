import random
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.charger import Charger
from app.models.enums import ChargerModel, ChargerStatus
from app.models.establishment import Establishment
from simulador.historical_generator import AnomalyPlan, generate_charger_history


def _build_charger(kind: str = "estacionamento") -> Charger:
    establishment = Establishment(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name="Estabelecimento Teste",
        kind=kind,
        phase="trifasico",
        grid_connection_kw=Decimal("75.000"),
        power_limit_kw=Decimal("40.000"),
    )
    charger = Charger(
        id=uuid.uuid4(),
        establishment_id=establishment.id,
        sems_serial="HCA-G2-TEST-001",
        model=ChargerModel.gw11k,
        spot_label="Vaga 01",
        status=ChargerStatus.livre,
        nominal_power_kw=Decimal("11.000"),
    )
    charger.establishment = establishment
    return charger


def test_timestamps_are_strictly_increasing_per_charger():
    charger = _build_charger()
    window_end = datetime(2026, 8, 24, tzinfo=UTC)
    window_start = window_end - timedelta(days=5)
    rows = generate_charger_history(
        charger, window_start, window_end, random.Random(42), AnomalyPlan()
    )

    timestamps = [row["timestamp"] for row in rows]
    assert len(timestamps) > 1
    for previous, current in zip(timestamps, timestamps[1:]):
        assert current > previous


def test_energy_regresses_only_at_the_planned_reset_day():
    charger = _build_charger()
    window_end = datetime(2026, 8, 24, tzinfo=UTC)
    window_start = window_end - timedelta(days=10)
    reset_day = (window_end - timedelta(days=3)).date()

    plan = AnomalyPlan()
    plan.energy_reset.add((charger.id, reset_day))

    rows = generate_charger_history(charger, window_start, window_end, random.Random(42), plan)
    totals = [row["total_energy_kwh"] for row in rows]

    regressions = [i for i in range(1, len(totals)) if totals[i] < totals[i - 1]]
    assert len(regressions) == 1


def test_same_seed_produces_identical_output():
    window_end = datetime(2026, 8, 24, tzinfo=UTC)
    window_start = window_end - timedelta(days=7)

    charger_a = _build_charger()
    rows_a = generate_charger_history(
        charger_a, window_start, window_end, random.Random(123), AnomalyPlan()
    )

    charger_b = _build_charger()
    charger_b.id = charger_a.id
    rows_b = generate_charger_history(
        charger_b, window_start, window_end, random.Random(123), AnomalyPlan()
    )

    assert [(r["timestamp"], r["power_kw"], r["total_energy_kwh"]) for r in rows_a] == [
        (r["timestamp"], r["power_kw"], r["total_energy_kwh"]) for r in rows_b
    ]
