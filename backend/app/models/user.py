import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.establishment import Establishment
    from app.models.tariff import Plan


class Company(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Modo empresarial: frota de uma empresa cliente vinculada a um estabelecimento."""

    __tablename__ = "companies"

    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))
    name: Mapped[str] = mapped_column(String(150))
    cost_center: Mapped[str | None] = mapped_column(String(50))

    establishment: Mapped["Establishment"] = relationship(back_populates="companies")
    employees: Mapped[list["User"]] = relationship(back_populates="company")


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role"))
    full_name: Mapped[str] = mapped_column(String(150))
    vehicle_model: Mapped[str | None] = mapped_column(String(100))
    rfid_virtual_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("companies.id"))

    company: Mapped["Company | None"] = relationship(back_populates="employees")
    owned_establishments: Mapped[list["Establishment"]] = relationship(back_populates="owner")


class Subscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id"))
    billing_cycle_start: Mapped[date] = mapped_column(Date)
    billing_cycle_end: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship()
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")
