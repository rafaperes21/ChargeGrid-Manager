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

    # Limites da sugestao de precificacao dinamica do modulo de IA (skill
    # ml-previsao-e-anomalias secao 2). So limitam a SUGESTAO exibida ao proprietario -
    # a IA nunca aplica tarifa sozinha, entao nao ha risco de estouro automatico.
    max_increase_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("20.00"))
    max_decrease_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("20.00"))

    # Numeric(9,6): 3 casas antes do ponto cobrem +-180 de longitude, 6 casas depois dao
    # precisao de ~11 cm - de sobra para o Haversine do mapa do cliente (Tarefa 2.1).
    # Opcionais: estabelecimentos antigos podem nao ter coordenada cadastrada ainda.
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), default=None)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), default=None)

    # CSV de PaymentMethod (mesmo padrao de TariffRule.days_of_week) - formas de pagamento
    # que este estabelecimento aceita (M3, Tarefa 4.2). Exposto como lista via a property
    # abaixo; nunca processa pagamento, so registra o que o proprietario diz aceitar.
    accepted_payment_methods_csv: Mapped[str] = mapped_column(String(120), default="")

    @property
    def accepted_payment_methods(self) -> list[str]:
        return [v for v in self.accepted_payment_methods_csv.split(",") if v]

    @accepted_payment_methods.setter
    def accepted_payment_methods(self, values: list[str]) -> None:
        self.accepted_payment_methods_csv = ",".join(values)

    owner: Mapped["User"] = relationship(back_populates="owned_establishments")
    chargers: Mapped[list["Charger"]] = relationship(back_populates="establishment")
    plans: Mapped[list["Plan"]] = relationship(back_populates="establishment")
    tariff_rules: Mapped[list["TariffRule"]] = relationship(back_populates="establishment")
    companies: Mapped[list["Company"]] = relationship(back_populates="establishment")
