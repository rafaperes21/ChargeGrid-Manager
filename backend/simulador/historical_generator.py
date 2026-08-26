"""Gerador de historico retroativo de `charger_readings`, para o Prophet/LSTM ter o que
treinar no dia 1 e para a deteccao de anomalias ter o que pegar na demo.

Uso: `cd backend && python -m simulador.historical_generator --seed 42`
(com o venv ativado, `.env` apontando para o Postgres e `python -m app.db.seed` ja rodado).

Ver skill `integracao-sems-simulador`, secao 5: 60-90 dias com semente fixa (`--seed`), e os
4 cenarios de anomalia injetados nos ultimos 7 dias da janela, para ficar facil de achar na
demo sem paginar o historico inteiro.
"""

import argparse
import itertools
import random
import sys
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session, joinedload, sessionmaker

from app.db.session import SessionLocal
from app.models.charger import Charger, ChargerReading
from simulador.anomalies import (
    energy_reset_drop,
    inject_over_nominal_spike,
    inject_zero_power_stall,
)
from simulador.curve_engine import generate_idle_samples, generate_session_samples
from simulador.energy import trapezoidal_energy_kwh
from simulador.profiles import PROFILE_BY_KIND, sessions_for_day
from simulador.vehicles import pick_vehicle

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
IDLE_SAMPLE_INTERVAL = timedelta(minutes=15)
ANOMALY_LOOKBACK_DAYS = 7
MIN_IDLE_GAP_HEADROOM = timedelta(minutes=30)
DEFAULT_DAYS_MIN = 60
DEFAULT_DAYS_MAX = 90


@dataclass
class AnomalyPlan:
    zero_power_stall: set[tuple[uuid.UUID, date]] = field(default_factory=set)
    over_nominal_spike: set[tuple[uuid.UUID, date]] = field(default_factory=set)
    energy_reset: set[tuple[uuid.UUID, date]] = field(default_factory=set)
    offline_gap: dict[tuple[uuid.UUID, date], timedelta] = field(default_factory=dict)


def load_chargers(db: Session) -> list[Charger]:
    chargers = (
        db.query(Charger).options(joinedload(Charger.establishment)).order_by(Charger.sems_serial).all()
    )
    if not chargers:
        print(
            "Nenhum carregador encontrado. Rode `python -m app.db.seed` antes do gerador de "
            "historico.",
            file=sys.stderr,
        )
        sys.exit(1)
    return chargers


def plan_anomalies(
    chargers: list[Charger], rng: random.Random, window_start: datetime, window_end: datetime
) -> AnomalyPlan:
    """Escolhe reprodutivelmente 1 ocorrencia de cada tipo de anomalia, de preferencia em
    carregadores distintos, sempre nos ultimos dias da janela (facil de achar na demo)."""
    plan = AnomalyPlan()
    if not chargers:
        return plan

    last_days = [
        window_end.date() - timedelta(days=offset) for offset in range(1, ANOMALY_LOOKBACK_DAYS + 1)
    ]
    last_days = [day for day in last_days if day >= window_start.date()]
    if not last_days:
        last_days = [window_start.date()]

    shuffled = list(chargers)
    rng.shuffle(shuffled)
    charger_cycle = itertools.cycle(shuffled)

    zero_power_charger = next(charger_cycle)
    plan.zero_power_stall.add((zero_power_charger.id, rng.choice(last_days)))

    over_nominal_charger = next(charger_cycle)
    plan.over_nominal_spike.add((over_nominal_charger.id, rng.choice(last_days)))

    energy_reset_charger = next(charger_cycle)
    plan.energy_reset.add((energy_reset_charger.id, rng.choice(last_days)))

    offline_charger = next(charger_cycle)
    offline_day = rng.choice(last_days)
    plan.offline_gap[(offline_charger.id, offline_day)] = timedelta(minutes=rng.randint(45, 90))

    return plan


def generate_charger_history(
    charger: Charger,
    window_start: datetime,
    window_end: datetime,
    rng: random.Random,
    plan: AnomalyPlan,
) -> list[dict]:
    """Gera as leituras de um carregador para a janela inteira: sessoes de carregamento
    (curve_engine + profiles) intercaladas com leituras ociosas, acumulando
    total_energy_kwh via trapezio e aplicando as anomalias planejadas para este charger."""
    kind = charger.establishment.kind if charger.establishment else "estacionamento"
    profile = PROFILE_BY_KIND.get(kind, PROFILE_BY_KIND["estacionamento"])

    rows: list[dict] = []
    running_total = Decimal("0.000")
    last_ts: datetime | None = None
    last_power = Decimal("0.000")
    gap_applied_days: set[date] = set()
    reset_applied_days: set[date] = set()

    def emit(ts: datetime, power_kw: Decimal, status, error_code: str | None = None) -> None:
        nonlocal running_total, last_ts, last_power
        if last_ts is not None and ts > last_ts:
            elapsed_hours = Decimal((ts - last_ts).total_seconds()) / Decimal("3600")
            running_total += trapezoidal_energy_kwh(last_power, power_kw, elapsed_hours)

        day = ts.astimezone(LOCAL_TZ).date()
        reset_key = (charger.id, day)
        if reset_key in plan.energy_reset and day not in reset_applied_days:
            running_total = energy_reset_drop(running_total, rng)
            reset_applied_days.add(day)

        last_ts, last_power = ts, power_kw
        rows.append(
            {
                "charger_id": charger.id,
                "timestamp": ts,
                "power_kw": power_kw,
                "status": status,
                "total_energy_kwh": running_total,
                "error_code": error_code,
            }
        )

    def emit_idle(start: datetime, end: datetime) -> None:
        if start >= end:
            return
        day = start.astimezone(LOCAL_TZ).date()
        gap_key = (charger.id, day)
        gap_duration = plan.offline_gap.get(gap_key)

        min_span = None if gap_duration is None else gap_duration + MIN_IDLE_GAP_HEADROOM
        enough_room = min_span is not None and (end - start) > min_span
        if enough_room and day not in gap_applied_days:
            midpoint = start + (end - start) / 2
            for ts, power, status in generate_idle_samples(start, midpoint, IDLE_SAMPLE_INTERVAL):
                emit(ts, power, status)
            gap_applied_days.add(day)
            resume = midpoint + gap_duration
            for ts, power, status in generate_idle_samples(resume, end, IDLE_SAMPLE_INTERVAL):
                emit(ts, power, status)
        else:
            for ts, power, status in generate_idle_samples(start, end, IDLE_SAMPLE_INTERVAL):
                emit(ts, power, status)

    cursor = window_start
    current_day = window_start.date()
    end_day = window_end.date()

    while current_day < end_day:
        session_local_times = sessions_for_day(profile, current_day, rng)
        session_starts_utc = sorted(
            datetime.combine(current_day, local_time, tzinfo=LOCAL_TZ).astimezone(UTC)
            for local_time in session_local_times
        )

        for session_start in session_starts_utc:
            if session_start < cursor:
                continue

            emit_idle(cursor, session_start)

            vehicle = pick_vehicle(rng)
            initial_soc = Decimal(str(round(rng.uniform(0.15, 0.60), 3)))
            target_soc = Decimal(str(round(rng.uniform(0.80, 1.0), 3)))
            samples = generate_session_samples(
                charger.nominal_power_kw, vehicle, initial_soc, target_soc, rng
            )

            if (charger.id, current_day) in plan.zero_power_stall:
                samples = inject_zero_power_stall(samples, rng)
            if (charger.id, current_day) in plan.over_nominal_spike:
                samples = inject_over_nominal_spike(samples, charger.nominal_power_kw, rng)

            for sample in samples:
                emit(
                    session_start + sample.offset, sample.power_kw, sample.status, sample.error_code
                )
            cursor = session_start + samples[-1].offset

        next_day = current_day + timedelta(days=1)
        day_end_utc = min(
            datetime.combine(next_day, time.min, tzinfo=LOCAL_TZ).astimezone(UTC), window_end
        )
        emit_idle(cursor, day_end_utc)
        # uma sessao longa pode atravessar a meia-noite local; nunca voltar o cursor para
        # tras do ultimo instante ja emitido.
        cursor = max(cursor, day_end_utc)
        current_day = next_day

    return rows


def bulk_insert_readings(db: Session, rows: Iterable[dict], batch_size: int) -> int:
    total = 0
    batch: list[dict] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= batch_size:
            db.execute(insert(ChargerReading), batch)
            total += len(batch)
            batch = []
    if batch:
        db.execute(insert(ChargerReading), batch)
        total += len(batch)
    db.commit()
    return total


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42, help="Semente para reprodutibilidade.")
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Numero exato de dias (sobrepoe --days-min/--days-max).",
    )
    parser.add_argument("--days-min", type=int, default=DEFAULT_DAYS_MIN)
    parser.add_argument("--days-max", type=int, default=DEFAULT_DAYS_MAX)
    parser.add_argument(
        "--database-url", type=str, default=None, help="Sobrepoe DATABASE_URL do .env."
    )
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument(
        "--force", action="store_true", help="Ignora a guarda de idempotencia e insere mesmo assim."
    )
    return parser


def main() -> None:
    args = _build_arg_parser().parse_args()
    rng = random.Random(args.seed)

    if args.database_url:
        engine = create_engine(args.database_url)
        db: Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    else:
        db = SessionLocal()

    try:
        chargers = load_chargers(db)
        charger_ids = [charger.id for charger in chargers]

        existing = (
            db.query(ChargerReading.id).filter(ChargerReading.charger_id.in_(charger_ids)).first()
        )
        if existing is not None and not args.force:
            print(
                "Ja existem leituras para estes carregadores - abortando para nao duplicar "
                "historico. Use --force para inserir mesmo assim.",
            )
            return

        days = args.days if args.days is not None else rng.randint(args.days_min, args.days_max)
        window_end = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        window_start = window_end - timedelta(days=days)

        plan = plan_anomalies(chargers, rng, window_start, window_end)

        all_rows: list[dict] = []
        for charger in chargers:
            all_rows.extend(generate_charger_history(charger, window_start, window_end, rng, plan))

        total_inserted = bulk_insert_readings(db, all_rows, args.batch_size)

        serial_by_id = {charger.id: charger.sems_serial for charger in chargers}
        print(f"Leituras inseridas: {total_inserted}")
        print(f"Carregadores: {len(chargers)} | Dias: {days} | Seed: {args.seed}")
        print("Anomalias injetadas:")
        for charger_id, day in plan.zero_power_stall:
            print(f"  - potencia zerada prolongada: {serial_by_id[charger_id]} em {day}")
        for charger_id, day in plan.over_nominal_spike:
            print(f"  - potencia acima da nominal: {serial_by_id[charger_id]} em {day}")
        for charger_id, day in plan.energy_reset:
            print(f"  - energia acumulada regredindo: {serial_by_id[charger_id]} em {day}")
        for (charger_id, day), gap in plan.offline_gap.items():
            gap_minutes = int(gap.total_seconds() // 60)
            print(f"  - offline por {gap_minutes} min: {serial_by_id[charger_id]} em {day}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
