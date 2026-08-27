"""Telemetria de um carregador individual - tela de detalhe do proprietario (M11: peca de
venda pra quem fabrica o hardware, mostra monitoramento granular por unidade fisica)."""

from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.charger import Charger, ChargerReading
from app.models.enums import ChargerStatus
from app.models.session import ChargingSession
from app.schemas.dashboard import ChargerDetailResponse, ChargerReadingPoint
from app.schemas.session import ChargingSessionRead
from app.services.dashboard import fetch_anomalies, latest_reading

RECENT_SESSIONS_LIMIT = 10


def _power_series(db: Session, charger_id, since: datetime) -> list[ChargerReading]:
    return (
        db.query(ChargerReading)
        .filter(ChargerReading.charger_id == charger_id, ChargerReading.timestamp >= since)
        .order_by(ChargerReading.timestamp.asc())
        .all()
    )


def uptime_pct(readings: list[ChargerReading]) -> Decimal | None:
    """Fracao das leituras na janela em que o status nao era offline. `None` (nunca 0%)
    quando nao ha nenhuma leitura ainda - "sem dado" e um estado real, o polling so
    acumula historico desde que o ambiente subiu (sem seed de leituras antigas)."""
    if not readings:
        return None
    online = sum(1 for reading in readings if reading.status != ChargerStatus.offline)
    return (Decimal(online) / Decimal(len(readings))).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )


def _recent_sessions(db: Session, charger_id) -> list[ChargingSession]:
    return (
        db.query(ChargingSession)
        .filter(ChargingSession.charger_id == charger_id)
        .order_by(ChargingSession.started_at.desc())
        .limit(RECENT_SESSIONS_LIMIT)
        .all()
    )


def get_charger_detail(
    db: Session, charger: Charger, settings: Settings, hours: int = 24
) -> ChargerDetailResponse:
    since = datetime.now(tz=UTC) - timedelta(hours=hours)
    readings = _power_series(db, charger.id, since)
    latest = latest_reading(db, charger.id)

    anomalies, ia_unavailable = fetch_anomalies(charger.establishment_id, settings)
    charger_anomalies = [a for a in anomalies if a.charger_serial == charger.sems_serial]

    return ChargerDetailResponse(
        id=charger.id,
        spot_label=charger.spot_label,
        sems_serial=charger.sems_serial,
        model=charger.model,
        status=charger.status,
        nominal_power_kw=charger.nominal_power_kw,
        latest_power_kw=latest.power_kw if latest else None,
        latest_reading_at=latest.timestamp if latest else None,
        uptime_pct=uptime_pct(readings),
        readings_window_hours=hours,
        power_readings=[
            ChargerReadingPoint(timestamp=r.timestamp, power_kw=r.power_kw, status=r.status)
            for r in readings
        ],
        recent_sessions=[
            ChargingSessionRead.model_validate(session)
            for session in _recent_sessions(db, charger.id)
        ],
        anomalies=charger_anomalies,
        ia_unavailable=ia_unavailable,
    )
