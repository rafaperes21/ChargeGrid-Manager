"""Agrega dado real (carregadores, ultima leitura, anomalias da IA, receita e sessoes ativas)
pro dashboard do proprietario.
"""

from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

import requests
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.charger import Charger, ChargerReading
from app.models.enums import ChargingSessionStatus
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.schemas.dashboard import ChargerDashboardItem, DashboardAnomaly, DashboardResponse

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")


def _as_utc(value: datetime) -> datetime:
    """SQLite (usado nos testes) nao preserva tzinfo em `DateTime(timezone=True)` -
    devolve naive na leitura, mesmo o valor tendo sido salvo com timezone. Postgres (prod)
    preserva. Normaliza pra UTC nos dois casos - convencao do projeto e tudo em UTC no banco."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _revenue_breakdown(
    db: Session, establishment_id, now_utc: datetime
) -> tuple[Decimal, Decimal, Decimal]:
    """Receita de hoje, da semana (segunda-feira local ate agora) e do mes (dia 1 local ate
    agora), num unico passo pelas sessoes finalizadas - evita tres queries separadas."""
    finished = (
        db.query(ChargingSession)
        .filter(
            ChargingSession.establishment_id == establishment_id,
            ChargingSession.status == ChargingSessionStatus.finished,
            ChargingSession.ended_at.is_not(None),
        )
        .all()
    )

    today_local = now_utc.astimezone(LOCAL_TZ).date()
    week_start_local = today_local - timedelta(days=today_local.weekday())
    month_start_local = today_local.replace(day=1)

    revenue_today = Decimal("0.0000")
    revenue_week = Decimal("0.0000")
    revenue_month = Decimal("0.0000")
    for session in finished:
        ended_local_date = _as_utc(session.ended_at).astimezone(LOCAL_TZ).date()
        if ended_local_date == today_local:
            revenue_today += session.amount_due
        if ended_local_date >= week_start_local:
            revenue_week += session.amount_due
        if ended_local_date >= month_start_local:
            revenue_month += session.amount_due

    return revenue_today, revenue_week, revenue_month


def _active_sessions_count(db: Session, establishment_id) -> int:
    return (
        db.query(ChargingSession)
        .filter(
            ChargingSession.establishment_id == establishment_id,
            ChargingSession.status == ChargingSessionStatus.active,
        )
        .count()
    )


def _latest_reading(db: Session, charger_id) -> ChargerReading | None:
    return (
        db.query(ChargerReading)
        .filter(ChargerReading.charger_id == charger_id)
        .order_by(ChargerReading.timestamp.desc())
        .first()
    )


def _fetch_anomalies(establishment_id, settings: Settings) -> tuple[list[DashboardAnomaly], bool]:
    url = f"{settings.ia_service_url}/anomalies/establishments/{establishment_id}"
    try:
        response = requests.get(url, params={"lookback_hours": 168}, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return [], True

    data = response.json()
    anomalies = [
        DashboardAnomaly(
            charger_serial=alert["charger_serial"],
            rule=alert["rule"],
            severity=alert["severity"],
            message=alert["message"],
        )
        for alert in data.get("alerts", [])
    ]
    return anomalies, False


def get_dashboard(
    db: Session, establishment: Establishment, settings: Settings
) -> DashboardResponse:
    chargers = (
        db.query(Charger)
        .filter(Charger.establishment_id == establishment.id)
        .order_by(Charger.spot_label)
        .all()
    )

    items = []
    total_power_kw = Decimal("0.000")
    for charger in chargers:
        reading = _latest_reading(db, charger.id)
        latest_power = reading.power_kw if reading else None
        if latest_power is not None:
            total_power_kw += latest_power
        items.append(
            ChargerDashboardItem(
                id=charger.id,
                spot_label=charger.spot_label,
                sems_serial=charger.sems_serial,
                model=charger.model,
                status=charger.status,
                nominal_power_kw=charger.nominal_power_kw,
                latest_power_kw=latest_power,
                latest_reading_at=reading.timestamp if reading else None,
            )
        )

    power_pct = None
    if establishment.power_limit_kw > 0:
        power_pct = (total_power_kw / establishment.power_limit_kw).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

    anomalies, ia_unavailable = _fetch_anomalies(establishment.id, settings)
    now_utc = datetime.now(tz=UTC)
    revenue_today, revenue_week, revenue_month = _revenue_breakdown(
        db, establishment.id, now_utc
    )

    return DashboardResponse(
        establishment_id=establishment.id,
        establishment_name=establishment.name,
        chargers=items,
        total_power_kw=total_power_kw,
        power_limit_kw=establishment.power_limit_kw,
        power_pct=power_pct,
        anomalies=anomalies,
        ia_unavailable=ia_unavailable,
        revenue_today=revenue_today,
        revenue_week=revenue_week,
        revenue_month=revenue_month,
        active_sessions_count=_active_sessions_count(db, establishment.id),
    )
