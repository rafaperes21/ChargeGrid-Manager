import uuid
from typing import Literal

from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    establishment_id: uuid.UUID
    message: str
    history: list[ChatMessageIn] = []


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[str]
