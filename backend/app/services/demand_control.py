"""Controle de demanda - Sprint 4 (Fase 1).

Antes desta fase o sistema so ALERTAVA quando a potencia somada passava de 90% do limite
contratado (`services/dashboard.py`); nada limitava os carregadores de fato. Aqui o limite vira
regra: a potencia disponivel (rede ate `power_limit_kw` + solar + descarga possivel da
bateria) e repartida entre os carregadores com sessao aberta.

Regra de reparticao: proporcional ao que cada carregador pede (sua potencia nominal), nunca
acima do pedido. Proporcional em vez de "primeiro que chegou leva tudo" porque nenhum cliente
fica parado esperando - todos carregam, mais devagar, e o tempo extra se distribui igual.

Funcao pura (sem banco), testavel isoladamente e reaproveitada pelo polling ao vivo e pelo
script de cenarios (`backend/scripts/cenarios.py`).
"""

from collections.abc import Hashable, Mapping
from decimal import ROUND_DOWN, Decimal

_KW = Decimal("0.001")
_ZERO = Decimal("0")


def allocate_power(
    requested_kw: Mapping[Hashable, Decimal], available_kw: Decimal
) -> dict[Hashable, Decimal]:
    """Teto de potencia (kW) por carregador. Se a soma pedida cabe no disponivel, cada um
    recebe o que pediu; senao, todos sao reduzidos pelo mesmo fator.

    Arredonda para BAIXO (3 casas) para a soma dos tetos nunca passar do disponivel por
    causa de arredondamento - passar 1 W do limite contratado e multa de demanda.
    """
    available_kw = max(_ZERO, available_kw)
    requested = {key: max(_ZERO, value) for key, value in requested_kw.items()}
    total = sum(requested.values(), _ZERO)
    if total <= available_kw:
        return dict(requested)

    factor = available_kw / total
    return {
        key: (value * factor).quantize(_KW, rounding=ROUND_DOWN)
        for key, value in requested.items()
    }
