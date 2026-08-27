"""Motor de calculo puro do valor de uma sessao de carregamento (M3).

Ordem fixa de aplicacao (skill tarifacao-e-sessoes, secao 3), nao inverter:
bruto -> minutos gratuitos (promocao) -> desconto do plano (%) -> franquia (kWh) -> valor final.
O desconto do plano incide sobre o valor ja promocional, nunca sobre o bruto.

Sem I/O e sem acesso a banco - os valores (tarifa, desconto, franquia disponivel) sao
resolvidos por quem chama (services/sessions.py) e o resultado vira snapshot em
ChargingSession. Nunca reprocessar contra tariff_rules/plans atuais depois do fechamento.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

ENERGY_QUANT = Decimal("0.001")
MONEY_QUANT = Decimal("0.0001")


def _quant(value: Decimal, exp: Decimal) -> Decimal:
    return value.quantize(exp, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PricingResult:
    gross_amount: Decimal
    promo_kwh_deducted: Decimal
    free_minutes_applied: int
    billed_kwh_after_promo: Decimal
    plan_discount_pct: Decimal
    franquia_kwh_used: Decimal
    billed_kwh_final: Decimal
    final_amount: Decimal


def calculate_session_amount(
    *,
    energy_kwh: Decimal,
    tariff_rate_per_kwh: Decimal,
    session_duration_minutes: Decimal = Decimal("0"),
    free_minutes: int = 0,
    plan_discount_pct: Decimal = Decimal("0"),
    franquia_kwh_available: Decimal = Decimal("0"),
) -> PricingResult:
    if energy_kwh < 0:
        raise ValueError("energy_kwh nao pode ser negativo")
    if tariff_rate_per_kwh < 0:
        raise ValueError("tariff_rate_per_kwh nao pode ser negativo")
    if free_minutes < 0:
        raise ValueError("free_minutes nao pode ser negativo")
    if not (Decimal("0") <= plan_discount_pct <= Decimal("100")):
        raise ValueError("plan_discount_pct deve estar entre 0 e 100")
    if franquia_kwh_available < 0:
        raise ValueError("franquia_kwh_available nao pode ser negativo")

    # 1. bruto
    gross_amount = energy_kwh * tariff_rate_per_kwh

    # 2. minutos gratuitos convertidos em kWh, proporcional a potencia media da sessao
    # (energia e tempo sao proporcionais a potencia constante media, entao o fator kW
    # se cancela: promo_kwh = energia_total * minutos_gratis / duracao_total).
    promo_kwh = Decimal("0")
    applied_free_minutes = 0
    if free_minutes > 0 and session_duration_minutes > 0 and energy_kwh > 0:
        promo_kwh = min(energy_kwh, energy_kwh * Decimal(free_minutes) / session_duration_minutes)
        applied_free_minutes = free_minutes

    billed_kwh_after_promo = energy_kwh - promo_kwh
    amount_after_promo = billed_kwh_after_promo * tariff_rate_per_kwh

    # 3. desconto do plano sobre o valor ja promocional (nao sobre o bruto)
    discount_factor = Decimal("1") - (plan_discount_pct / Decimal("100"))
    amount_after_discount = amount_after_promo * discount_factor

    # 4. franquia abatida em kWh, antes de virar dinheiro. Equivale algebricamente a
    # remover essas unidades pelo preco por kWh ja com promocao+desconto aplicados
    # (distributividade: (e - f) * r * d == e*r*d - f*r*d), entao converter aqui em
    # vez de antes do passo 2/3 chega no mesmo valor final.
    discounted_rate = tariff_rate_per_kwh * discount_factor
    franquia_kwh_used = min(billed_kwh_after_promo, franquia_kwh_available)
    franquia_value = franquia_kwh_used * discounted_rate

    final_amount = amount_after_discount - franquia_value
    billed_kwh_final = billed_kwh_after_promo - franquia_kwh_used

    return PricingResult(
        gross_amount=_quant(gross_amount, MONEY_QUANT),
        promo_kwh_deducted=_quant(promo_kwh, ENERGY_QUANT),
        free_minutes_applied=applied_free_minutes,
        billed_kwh_after_promo=_quant(billed_kwh_after_promo, ENERGY_QUANT),
        plan_discount_pct=plan_discount_pct,
        franquia_kwh_used=_quant(franquia_kwh_used, ENERGY_QUANT),
        billed_kwh_final=_quant(billed_kwh_final, ENERGY_QUANT),
        final_amount=_quant(final_amount, MONEY_QUANT),
    )
