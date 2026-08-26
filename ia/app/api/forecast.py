import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.forecast import ForecastResponse
from app.services.forecast import get_forecast

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/establishments/{establishment_id}/demand", response_model=ForecastResponse)
def get_demand_forecast(
    establishment_id: uuid.UUID,
    horizon_hours: int = settings.forecast_default_horizon_hours,
    db: Session = Depends(get_db),
) -> ForecastResponse:
    return get_forecast(db, establishment_id, horizon_hours, settings)
