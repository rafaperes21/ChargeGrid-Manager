import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.charger import Charger
    from app.models.establishment import Establishment


class Alert(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "alerts"

    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))
    charger_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chargers.id"))
    kind: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(String(500))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    establishment: Mapped["Establishment"] = relationship()
    charger: Mapped["Charger | None"] = relationship()
