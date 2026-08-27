import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.pricing_suggestion import PricingSuggestionResponse
from app.services.pricing_suggestion import get_pricing_suggestions

router = APIRouter(prefix="/pricing-suggestions", tags=["pricing-suggestions"])


@router.get("/establishments/{establishment_id}", response_model=PricingSuggestionResponse)
def get_pricing_suggestions_for_establishment(
    establishment_id: uuid.UUID,
    horizon_hours: int = settings.forecast_default_horizon_hours,
    db: Session = Depends(get_db),
) -> PricingSuggestionResponse:
    return get_pricing_suggestions(db, establishment_id, horizon_hours, settings)
