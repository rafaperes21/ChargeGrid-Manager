"""Fechamento financeiro por periodo (M4 - Relatorios). Mesma ideia de
`services/dashboard._revenue_breakdown`, mas com limites de data escolhidos por quem chama
em vez de dia/semana/mes corrente - agrega uma unica vez sobre sessoes `finished`.
"""

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.charger import Charger
from app.models.enums import ChargingSessionStatus
from app.models.session import ChargingSession
from app.schemas.reports import (
    ChargerOccupancy,
    DailyRevenuePoint,
    OccupancyResponse,
    ReportResponse,
)

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
MONEY_QUANT = Decimal("0.0001")


def _as_utc(value: datetime) -> datetime:
    """SQLite (usado nos testes) nao preserva tzinfo em `DateTime(timezone=True)` -
    devolve naive na leitura, mesmo o valor tendo sido salvo com timezone. Postgres (prod)
    preserva. Normaliza pra UTC nos dois casos - convencao do projeto e tudo em UTC no banco."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def default_period() -> tuple[date, date]:
    """Mes corrente (horario local), do dia 1 ate hoje - usado quando from/to nao sao
    informados."""
    today_local = datetime.now(tz=UTC).astimezone(LOCAL_TZ).date()
    return today_local.replace(day=1), today_local


def get_report(
    db: Session, establishment_id, from_date: date, to_date: date
) -> ReportResponse:
    finished = (
        db.query(ChargingSession)
        .filter(
            ChargingSession.establishment_id == establishment_id,
            ChargingSession.status == ChargingSessionStatus.finished,
            ChargingSession.ended_at.is_not(None),
        )
        .all()
    )

    revenue_total = Decimal("0.0000")
    energy_total = Decimal("0.000")
    completed_count = 0
    daily_totals: dict[date, Decimal] = defaultdict(lambda: Decimal("0.0000"))

    for session in finished:
        ended_local_date = _as_utc(session.ended_at).astimezone(LOCAL_TZ).date()
        if not (from_date <= ended_local_date <= to_date):
            continue
        revenue_total += session.amount_due or Decimal("0.0000")
        energy_total += session.energy_kwh or Decimal("0.000")
        completed_count += 1
        daily_totals[ended_local_date] += session.amount_due or Decimal("0.0000")

    average_ticket = None
    if completed_count > 0:
        average_ticket = (revenue_total / completed_count).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )

    return ReportResponse(
        establishment_id=establishment_id,
        from_date=from_date,
        to_date=to_date,
        revenue_total=revenue_total,
        completed_sessions_count=completed_count,
        average_ticket=average_ticket,
        total_energy_kwh=energy_total,
        daily_revenue=[
            DailyRevenuePoint(date=d, revenue=v) for d, v in sorted(daily_totals.items())
        ],
    )


def get_charger_occupancy(
    db: Session, establishment_id, from_date: date, to_date: date
) -> OccupancyResponse:
    """Uma linha por vaga - quantas sessoes, quanta energia/receita e quantas horas de
    carregamento cada carregador teve no periodo. Base do grafico 'ocupacao por vaga'
    (visao de mercado: qual vaga rende mais) - so soma sessao `finished` real, igual
    `get_report`, nunca estima ocupacao a partir de status atual."""
    chargers = (
        db.query(Charger)
        .filter(Charger.establishment_id == establishment_id)
        .order_by(Charger.spot_label)
        .all()
    )

    empty_bucket = {
        "sessions_count": 0,
        "energy_kwh": Decimal("0.000"),
        "revenue": Decimal("0.0000"),
        "hours_charged": Decimal("0.00"),
    }
    by_charger: dict = defaultdict(lambda: dict(empty_bucket))

    finished = (
        db.query(ChargingSession)
        .filter(
            ChargingSession.establishment_id == establishment_id,
            ChargingSession.status == ChargingSessionStatus.finished,
            ChargingSession.ended_at.is_not(None),
        )
        .all()
    )
    for session in finished:
        ended_local_date = _as_utc(session.ended_at).astimezone(LOCAL_TZ).date()
        if not (from_date <= ended_local_date <= to_date):
            continue
        bucket = by_charger[session.charger_id]
        bucket["sessions_count"] += 1
        bucket["energy_kwh"] += session.energy_kwh or Decimal("0.000")
        bucket["revenue"] += session.amount_due or Decimal("0.0000")
        duration_hours = Decimal(
            (_as_utc(session.ended_at) - _as_utc(session.started_at)).total_seconds()
        ) / Decimal("3600")
        bucket["hours_charged"] += duration_hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return OccupancyResponse(
        establishment_id=establishment_id,
        from_date=from_date,
        to_date=to_date,
        chargers=[
            ChargerOccupancy(
                charger_id=charger.id,
                spot_label=charger.spot_label,
                **by_charger.get(charger.id, empty_bucket),
            )
            for charger in chargers
        ],
    )
