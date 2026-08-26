"""Calculadora de dimensionamento do HCA G2 - skill `dimensionamento-hca-g2`, formulas
exatas das secoes 3, 4 e 5. Funcoes puras, sem I/O - testaveis sem HTTP.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import ChargerModel
from app.services.charger_catalog import CHARGER_SPECS

SAFETY_MARGIN = Decimal("0.80")

# Fator de simultaneidade por tipo de estabelecimento - mesmas chaves ja usadas em
# `Establishment.kind` no projeto (nao a nomenclatura em ingles da skill).
DIVERSITY_FACTOR: dict[str, Decimal] = {
    "shopping": Decimal("0.60"),
    "estacionamento": Decimal("0.70"),
    "empresa": Decimal("0.85"),
}


def select_model(phase: str, available_power_kw: Decimal) -> ChargerModel:
    """Fase mono -> unico elegivel e o GW7K. Fase tri -> GW22K se sobrar carga para pelo
    menos 2 pontos, senao GW11K (empate favorece o GW11K - skill secao 3)."""
    if phase == "monofasico":
        return ChargerModel.gw7k

    gw22k_power = CHARGER_SPECS[ChargerModel.gw22k].nominal_power_kw
    if available_power_kw >= 2 * gw22k_power:
        return ChargerModel.gw22k
    return ChargerModel.gw11k


def max_chargers(
    available_power_kw: Decimal, model: ChargerModel, establishment_type: str, parking_spots: int
) -> int:
    usable_kw = available_power_kw * SAFETY_MARGIN
    factor = DIVERSITY_FACTOR[establishment_type]
    nominal = CHARGER_SPECS[model].nominal_power_kw
    max_by_power = int(usable_kw / (nominal * factor))
    return min(max_by_power, parking_spots)


def min_power_required_kw(model: ChargerModel, establishment_type: str) -> Decimal:
    """Carga minima para pelo menos 1 ponto do modelo, dado o fator de simultaneidade -
    usado quando `max_chargers` da zero (skill: "nao devolva erro seco")."""
    factor = DIVERSITY_FACTOR[establishment_type]
    nominal = CHARGER_SPECS[model].nominal_power_kw
    return (nominal * factor / SAFETY_MARGIN).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Premissas padrao de payback (skill secao 5) - exibidas e editaveis pelo proprietario no PDF.
KWH_MEDIO_SESSAO = Decimal("22")
SESSOES_DIA_POR_PONTO: dict[str, Decimal] = {
    "shopping": Decimal("3.5"),
    "estacionamento": Decimal("2.5"),
    "empresa": Decimal("1.5"),
}
CUSTO_ENERGIA_KWH = Decimal("0.85")
CUSTO_INSTALACAO_PCT = Decimal("0.35")


def estimate_budget(
    model: ChargerModel, qty: int, establishment_type: str, tariff_per_kwh: Decimal
) -> dict:
    """`unit_price` e sempre `None` ate confirmacao do datasheet - por isso o orcamento
    sempre devolve "sob consulta" em vez de um capex/payback inventado (skill secao 5:
    "Nunca chute preco em documento que o proprietario vai levar para uma reuniao comercial")."""
    unit_price = CHARGER_SPECS[model].unit_price
    if unit_price is None:
        return {
            "capex": None,
            "payback_months": None,
            "note": (
                "Precos sob consulta - aguardando confirmacao do preco unitario no "
                "datasheet oficial da GoodWe."
            ),
        }

    capex = unit_price * qty * (Decimal("1") + CUSTO_INSTALACAO_PCT)
    sessoes_dia = SESSOES_DIA_POR_PONTO[establishment_type]
    margem_kwh = tariff_per_kwh - CUSTO_ENERGIA_KWH
    receita_mes = sessoes_dia * qty * KWH_MEDIO_SESSAO * margem_kwh * Decimal("30")
    payback_months = (capex / receita_mes) if receita_mes > 0 else None
    return {"capex": capex, "payback_months": payback_months, "note": None}
