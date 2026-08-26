"""Catalogo de especificacoes do GoodWe HCA G2, por modelo - skill `dimensionamento-hca-g2`.

TODO(datasheet): potencia nominal e `unit_price` sao valores comerciais padrao (base
230/400V), nao confirmados contra o datasheet oficial da GoodWe para rede brasileira
220/380V. `unit_price` fica `None` ate confirmacao - nunca inventar preco em orcamento que o
proprietario leva para uma reuniao comercial.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import ChargerModel


@dataclass(frozen=True)
class ChargerSpec:
    phase: str  # "monofasico" | "trifasico" - mesma convencao de Establishment.phase
    nominal_power_kw: Decimal
    max_current_a: Decimal
    unit_price: Decimal | None


CHARGER_SPECS: dict[ChargerModel, ChargerSpec] = {
    ChargerModel.gw7k: ChargerSpec(
        phase="monofasico",
        nominal_power_kw=Decimal("7.4"),
        max_current_a=Decimal("32"),
        unit_price=None,
    ),
    ChargerModel.gw11k: ChargerSpec(
        phase="trifasico",
        nominal_power_kw=Decimal("11.0"),
        max_current_a=Decimal("16"),
        unit_price=None,
    ),
    ChargerModel.gw22k: ChargerSpec(
        phase="trifasico",
        nominal_power_kw=Decimal("22.0"),
        max_current_a=Decimal("32"),
        unit_price=None,
    ),
}
