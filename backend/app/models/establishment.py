import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.charger import Charger
    from app.models.tariff import Plan, TariffRule
    from app.models.user import Company, User


class Establishment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "establishments"

    # use_alter: quebra o ciclo users -> companies -> establishments -> users.
    # Sem isso o Postgres nao consegue decidir em qual ordem criar as 3 tabelas.
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", use_alter=True, name="fk_establishments_owner_id")
    )
    name: Mapped[str] = mapped_column(String(150))
    kind: Mapped[str] = mapped_column(String(30))  # shopping | estacionamento | empresa
    phase: Mapped[str] = mapped_column(String(15))  # monofasico | bifasico | trifasico
    grid_connection_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    power_limit_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))

    owner: Mapped["User"] = relationship(back_populates="owned_establishments")
    chargers: Mapped[list["Charger"]] = relationship(back_populates="establishment")
    plans: Mapped[list["Plan"]] = relationship(back_populates="establishment")
    tariff_rules: Mapped[list["TariffRule"]] = relationship(back_populates="establishment")
    companies: Mapped[list["Company"]] = relationship(back_populates="establishment")
