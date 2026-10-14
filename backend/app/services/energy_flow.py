"""Consulta do fluxo de energia do estabelecimento (Sprint 4) - alimenta o painel do
proprietario, os relatorios e o assistente virtual. So leitura sobre `site_energy_readings`.

Energia por fonte = integral por trapezio das potencias (mesma formula das sessoes,
`services/energy_integration.py`), mas SEM arredondar intervalo a intervalo: aquela funcao
quantiza cada passo em 0,001 kWh (certo para o odometro de uma sessao), o que aqui, com
leituras de 1 min somadas ao longo de um mes, acumula erro visivel no % renovavel. Arredonda
so no total. Intervalos maiores que `MAX_GAP` (polling fora do ar) nao
sao integrados - sem dado, sem energia inventada.
"""

from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.energy import SiteEnergyReading
from app.models.establishment import Establishment
from app.schemas.energy import (
    EnergyAssetOut,
    EnergyFlowPoint,
    EnergyFlowResponse,
    EnergySummary,
)
from app.services.energy_assets import get_site_assets

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
MAX_GAP = timedelta(minutes=10)
SERIES_BUCKET = timedelta(minutes=5)
_KWH = Decimal("0.001")
_ZERO = Decimal("0")

_ENERGY_FIELDS = {
    "load_kwh": "load_kw",
    "solar_generated_kwh": "solar_kw",
    "solar_to_load_kwh": "solar_to_load_kw",
    "battery_to_load_kwh": "battery_to_load_kw",
    "grid_to_load_kwh": "grid_to_load_kw",
    "solar_to_battery_kwh": "solar_to_battery_kw",
    "solar_surplus_kwh": "solar_surplus_kw",
}
_POINT_FIELDS = [
    "load_kw", "solar_kw", "solar_to_load_kw", "battery_to_load_kw", "grid_to_load_kw",
    "solar_to_battery_kw", "solar_surplus_kw", "battery_kw", "grid_limit_kw",
    "demand_limited_kw",
]


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def local_day_bounds(from_date: date, to_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(from_date, time.min, tzinfo=LOCAL_TZ).astimezone(UTC)
    end = datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=LOCAL_TZ).astimezone(UTC)
    return start, end


def _readings(db: Session, establishment_id, start: datetime, end: datetime):
    return (
        db.query(SiteEnergyReading)
        .filter(
            SiteEnergyReading.establishment_id == establishment_id,
            SiteEnergyReading.timestamp >= start,
            SiteEnergyReading.timestamp < end,
        )
        .order_by(SiteEnergyReading.timestamp)
        .all()
    )


def summarize(readings: list[SiteEnergyReading], from_date: date, to_date: date) -> EnergySummary:
    totals = {key: _ZERO for key in _ENERGY_FIELDS}
    for before, after in zip(readings, readings[1:], strict=False):
        elapsed = _as_utc(after.timestamp) - _as_utc(before.timestamp)
        if elapsed <= timedelta(0) or elapsed > MAX_GAP:
            continue
        hours = Decimal(str(elapsed.total_seconds())) / Decimal(3600)
        for key, field in _ENERGY_FIELDS.items():
            totals[key] += (getattr(before, field) + getattr(after, field)) / 2 * hours

    load = totals["load_kwh"]
    renewable = totals["solar_to_load_kwh"] + totals["battery_to_load_kwh"]
    share = None
    if load > 0:
        share = (renewable / load * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        share = min(share, Decimal("100.0"))

    return EnergySummary(
        from_date=from_date,
        to_date=to_date,
        **{key: value.quantize(_KWH) for key, value in totals.items()},
        renewable_share_pct=share,
        peak_load_kw=max((r.load_kw for r in readings), default=_ZERO),
        peak_grid_kw=max((r.grid_to_load_kw for r in readings), default=_ZERO),
        readings_count=len(readings),
    )


def get_energy_summary(
    db: Session, establishment_id, from_date: date, to_date: date
) -> EnergySummary:
    start, end = local_day_bounds(from_date, to_date)
    return summarize(_readings(db, establishment_id, start, end), from_date, to_date)


def _to_point(reading: SiteEnergyReading) -> EnergyFlowPoint:
    return EnergyFlowPoint(
        timestamp=_as_utc(reading.timestamp),
        battery_soc_pct=reading.battery_soc_pct,
        **{field: getattr(reading, field) for field in _POINT_FIELDS},
    )


def _bucket_series(readings: list[SiteEnergyReading]) -> list[EnergyFlowPoint]:
    """Media por janela de 5 min - o grafico do dia nao precisa de 1440 pontos."""
    buckets: dict[datetime, list[SiteEnergyReading]] = {}
    seconds = int(SERIES_BUCKET.total_seconds())
    for reading in readings:
        ts = _as_utc(reading.timestamp)
        key = datetime.fromtimestamp(int(ts.timestamp()) // seconds * seconds, tz=UTC)
        buckets.setdefault(key, []).append(reading)

    points = []
    for key, group in sorted(buckets.items()):
        n = Decimal(len(group))
        socs = [r.battery_soc_pct for r in group if r.battery_soc_pct is not None]
        points.append(
            EnergyFlowPoint(
                timestamp=key,
                battery_soc_pct=(sum(socs) / len(socs)).quantize(Decimal("0.01"))
                if socs
                else None,
                **{
                    field: (sum(getattr(r, field) for r in group) / n).quantize(_KWH)
                    for field in _POINT_FIELDS
                },
            )
        )
    return points


def get_energy_flow(db: Session, establishment: Establishment) -> EnergyFlowResponse:
    inverter, battery = get_site_assets(db, establishment.id)
    today = datetime.now(UTC).astimezone(LOCAL_TZ).date()
    start, end = local_day_bounds(today, today)
    readings = _readings(db, establishment.id, start, end)

    latest_row = (
        db.query(SiteEnergyReading)
        .filter(SiteEnergyReading.establishment_id == establishment.id)
        .order_by(SiteEnergyReading.timestamp.desc())
        .first()
    )
    return EnergyFlowResponse(
        inverter=EnergyAssetOut.model_validate(inverter) if inverter else None,
        battery=EnergyAssetOut.model_validate(battery) if battery else None,
        latest=_to_point(latest_row) if latest_row else None,
        series=_bucket_series(readings),
        today=summarize(readings, today, today),
    )
