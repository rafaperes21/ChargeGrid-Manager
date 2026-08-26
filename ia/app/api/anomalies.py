import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import Charger
from app.schemas.anomalies import AnomalyReport
from app.services.anomalies import fetch_recent_readings, run_anomaly_rules

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("/establishments/{establishment_id}", response_model=AnomalyReport)
def get_anomaly_report(
    establishment_id: uuid.UUID,
    lookback_hours: int = settings.anomaly_default_lookback_hours,
    db: Session = Depends(get_db),
) -> AnomalyReport:
    chargers = db.execute(
        select(Charger).where(Charger.establishment_id == establishment_id)
    ).scalars().all()
    readings_by_charger = fetch_recent_readings(db, establishment_id, lookback_hours)

    alerts = []
    for charger in chargers:
        alerts += run_anomaly_rules(charger, readings_by_charger.get(charger.id, []), settings)

    return AnomalyReport(
        establishment_id=establishment_id,
        generated_at=datetime.now(tz=UTC),
        lookback_hours=lookback_hours,
        alerts=sorted(alerts, key=lambda alert: alert.window_start),
    )
