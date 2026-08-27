"""Fechamento financeiro por periodo (M4 - Relatorios). Mesma ideia de
`services/dashboard._revenue_breakdown`, mas com limites de data escolhidos por quem chama
em vez de dia/semana/mes corrente - agrega uma unica vez sobre sessoes `finished`.
"""

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.enums import ChargingSessionStatus
from app.models.session import ChargingSession
from app.schemas.reports import DailyRevenuePoint, ReportResponse

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
