import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.config import settings
from app.core.deps import require_customer, require_owner
from app.db.session import get_db
from app.models.user import User
from app.schemas.chatbot import ChatRequest, ChatResponse, CustomerChatRequest
from app.services.chatbot import run_chat, stream_chat
from app.services.chatbot_customer import run_customer_chat, stream_customer_chat

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


def _sse(events: Iterator[dict]) -> StreamingResponse:
    """Server-Sent Events: uma linha `data: {json}` por evento (`tool`, `token`, `done`).
    Gerador sincrono - o FastAPI roda num threadpool, sem travar o event loop."""

    def body() -> Iterator[str]:
        for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/message", response_model=ChatResponse)
def send_chat_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> ChatResponse:
    establishment = get_owned_establishment(payload.establishment_id, db, current_user)
    return run_chat(db, establishment, payload.message, payload.history, settings)


@router.post("/message/stream")
def stream_chat_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> StreamingResponse:
    """Mesma conversa de `/message`, transmitida token a token (SSE)."""
    establishment = get_owned_establishment(payload.establishment_id, db, current_user)
    return _sse(stream_chat(db, establishment, payload.message, payload.history, settings))


@router.post("/customer/message", response_model=ChatResponse)
def send_customer_chat_message(
    payload: CustomerChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> ChatResponse:
    return run_customer_chat(db, current_user, payload.message, payload.history, settings)


@router.post("/customer/message/stream")
def stream_customer_chat_message(
    payload: CustomerChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> StreamingResponse:
    return _sse(stream_customer_chat(db, current_user, payload.message, payload.history, settings))
