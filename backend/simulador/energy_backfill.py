"""Backfill de `site_energy_readings` a partir das leituras de carregadores ja existentes -
Sprint 4. Da historico de fluxo solar/bateria/rede para os relatorios e para a IA sem esperar
semanas de polling ao vivo.

Uso: `cd backend && python -m simulador.energy_backfill --days 30`

Como funciona (DADOS SIMULADOS - a carga vem do historico sintetico dos carregadores, o solar
da mesma curva do simulador ao vivo, `simulador/solar.py`):
- grade de `--step-minutes` (5 min) cobrindo os ultimos `--days` dias, parando antes da
  primeira leitura de fluxo ja gravada pelo polling ao vivo (nao sobrescreve dado ao vivo);
- carga de cada instante = soma da ultima leitura de cada carregador, se tiver no maximo
  20 min (mais velha que isso = sem dado -> 0, nunca inventa consumo);
- despacho com a mesma funcao do polling (`services/energy_dispatch.dispatch`), SoC
  encadeado instante a instante. Rede SEM limite: a carga historica ja aconteceu e precisa
  ter vindo de algum lugar - o controle de demanda nao existia quando ela foi gerada.
Idempotente: pula instantes que ja existem. `--force` apaga o intervalo e regera.
"""

import argparse
import bisect
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.charger import Charger, ChargerReading
from app.models.energy import SiteEnergyReading
from app.models.establishment import Establishment
from app.services.energy_assets import battery_free_discharge, battery_spec, get_site_assets
from app.services.energy_dispatch import dispatch
from simulador.solar import SolarParams, solar_power_kw

MAX_READING_AGE = timedelta(minutes=20)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _floor(ts: datetime, step: timedelta) -> datetime:
    seconds = int(step.total_seconds())
    return datetime.fromtimestamp(int(ts.timestamp()) // seconds * seconds, tz=UTC)


def build_rows(
    db: Session, establishment: Establishment, start: datetime, end: datetime, step: timedelta
) -> list[dict]:
    inverter, battery_asset = get_site_assets(db, establishment.id)
    spec = battery_spec(battery_asset)
    soc = Decimal(str(settings.sim_battery_initial_soc_pct)) if spec else None
    solar_params = (
        SolarParams(
            peak_kwp=inverter.rated_kw,
            sunrise_hour=settings.sim_solar_sunrise_hour,
            sunset_hour=settings.sim_solar_sunset_hour,
            performance_ratio=settings.sim_solar_performance_ratio,
            cloud_min=settings.sim_solar_cloud_min,
        )
        if inverter is not None and inverter.rated_kw
        else None
    )

    series = []  # por carregador: (timestamps ordenados, potencias)
    for charger in db.query(Charger).filter(Charger.establishment_id == establishment.id):
        rows = (
            db.query(ChargerReading.timestamp, ChargerReading.power_kw)
            .filter(
                ChargerReading.charger_id == charger.id,
                ChargerReading.timestamp >= start - MAX_READING_AGE,
                ChargerReading.timestamp < end,
            )
            .order_by(ChargerReading.timestamp)
            .all()
        )
        series.append(([_as_utc(ts) for ts, _ in rows], [power for _, power in rows]))

    dt_h = Decimal(str(step.total_seconds() / 3600))
    out = []
    t = _floor(start, step)
    while t < end:
        load = Decimal("0")
        for timestamps, powers in series:
            idx = bisect.bisect_right(timestamps, t) - 1
            if idx >= 0 and t - timestamps[idx] <= MAX_READING_AGE:
                load += powers[idx]
        solar = (
            solar_power_kw(inverter.sems_serial, t, solar_params)
            if solar_params
            else Decimal("0")
        )
        result = dispatch(
            load, solar, spec, soc, None, dt_h,
            battery_free_discharge=battery_free_discharge(battery_asset, t),
        )
        out.append(
            {
                "establishment_id": establishment.id,
                "timestamp": t,
                "load_kw": result.load_kw,
                "solar_kw": result.solar_kw,
                "solar_to_load_kw": result.solar_to_load_kw,
                "battery_to_load_kw": result.battery_to_load_kw,
                "grid_to_load_kw": result.grid_to_load_kw,
                "solar_to_battery_kw": result.solar_to_battery_kw,
                "solar_surplus_kw": result.solar_surplus_kw,
                "battery_kw": result.battery_kw,
                "battery_soc_pct": soc,
                "grid_limit_kw": establishment.power_limit_kw,
                "demand_limited_kw": Decimal("0"),
            }
        )
        soc = result.soc_after_pct
        t += step
    return out


def backfill(
    db: Session, establishment: Establishment, days: int, step: timedelta, force: bool
) -> int:
    end = datetime.now(UTC)
    first_live = (
        db.query(SiteEnergyReading.timestamp)
        .filter(SiteEnergyReading.establishment_id == establishment.id)
        .order_by(SiteEnergyReading.timestamp)
        .first()
    )
    start = end - timedelta(days=days)
    query = db.query(SiteEnergyReading).filter(
        SiteEnergyReading.establishment_id == establishment.id,
        SiteEnergyReading.timestamp >= start,
    )
    if force:
        query.delete(synchronize_session=False)
        db.commit()
    elif first_live is not None:
        end = min(end, _as_utc(first_live[0]))

    existing = {
        _as_utc(ts)
        for (ts,) in db.query(SiteEnergyReading.timestamp).filter(
            SiteEnergyReading.establishment_id == establishment.id,
            SiteEnergyReading.timestamp >= start,
            SiteEnergyReading.timestamp < end,
        )
    }
    rows = [
        row
        for row in build_rows(db, establishment, start, end, step)
        if row["timestamp"] not in existing
    ]
    for i in range(0, len(rows), 5000):
        db.bulk_insert_mappings(SiteEnergyReading, rows[i : i + 5000])
    db.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--step-minutes", type=int, default=5)
    parser.add_argument("--establishment-name", default="Estacionamento Central")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        establishment = (
            db.query(Establishment).filter(Establishment.name == args.establishment_name).first()
        )
        if establishment is None:
            print(f"Estabelecimento {args.establishment_name!r} nao encontrado.")
            return
        inserted = backfill(
            db, establishment, args.days, timedelta(minutes=args.step_minutes), args.force
        )
        print(f"{inserted} leituras de fluxo de energia geradas (dados simulados).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
