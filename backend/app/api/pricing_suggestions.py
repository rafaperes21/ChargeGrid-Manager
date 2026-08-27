import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.config import settings
from app.core.deps import require_owner
from app.db.session import get_db
from app.models.user import User
from app.schemas.pricing_suggestion import PricingSuggestionsResponse
from app.services.pricing_suggestions_proxy import fetch_pricing_suggestions

router = APIRouter(prefix="/pricing-suggestions", tags=["pricing-suggestions"])


@router.get("/establishments/{establishment_id}", response_model=PricingSuggestionsResponse)
def read_pricing_suggestions(
    establishment_id: uuid.UUID,
    horizon_hours: int = 48,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> PricingSuggestionsResponse:
    get_owned_establishment(establishment_id, db, current_user)
    return fetch_pricing_suggestions(establishment_id, horizon_hours, settings)
