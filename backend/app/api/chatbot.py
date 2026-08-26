from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.config import settings
from app.core.deps import require_owner
from app.db.session import get_db
from app.models.user import User
from app.schemas.chatbot import ChatRequest, ChatResponse
from app.services.chatbot import run_chat

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@router.post("/message", response_model=ChatResponse)
def send_chat_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> ChatResponse:
    establishment = get_owned_establishment(payload.establishment_id, db, current_user)
    return run_chat(db, establishment, payload.message, payload.history, settings)
