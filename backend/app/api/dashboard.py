import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.config import settings
from app.core.deps import require_owner
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import get_dashboard

router = APIRouter(prefix="/establishments", tags=["dashboard"])


@router.get("/{establishment_id}/dashboard", response_model=DashboardResponse)
def read_dashboard(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> DashboardResponse:
    establishment = get_owned_establishment(establishment_id, db, current_user)
    return get_dashboard(db, establishment, settings)
