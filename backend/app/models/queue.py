import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.establishment import Establishment
    from app.models.user import User


class QueueEntry(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "queue_entries"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()
    establishment: Mapped["Establishment"] = relationship()
