"""Integracao de energia entre leituras consecutivas, por trapezio.

Ver skill `integracao-sems-simulador`: multiplicar a ultima potencia pelo intervalo inteiro
superfatura o cliente na rampa de subida e subfatura na descida. Trapezio e obrigatorio.
Usado tanto pelo simulador (M2) quanto pelo motor de sessao (M3, `services/sessions.py`) -
formula unica, para nao divergir entre os dois lados.
"""

from decimal import ROUND_HALF_UP, Decimal

_ENERGY_QUANTIZE = Decimal("0.001")


def trapezoidal_energy_kwh(
    power_before_kw: Decimal, power_after_kw: Decimal, elapsed_hours: Decimal
) -> Decimal:
    """Delta de energia (kWh) entre duas leituras: (P_anterior + P_atual) / 2 x Delta_t_horas."""
    energy = (power_before_kw + power_after_kw) / Decimal("2") * elapsed_hours
    return energy.quantize(_ENERGY_QUANTIZE, rounding=ROUND_HALF_UP)
