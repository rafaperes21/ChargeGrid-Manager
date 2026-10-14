"""Curva de geracao solar do dia - Sprint 4 (Fase 1). Faz o papel do inversor GoodWe que, na
planta real, reportaria a potencia FV ao SEMS+.

Modelo (simplificado de proposito, parametrizavel):

    P(t) = kWp x PR x fator_do_dia x sen(pi x (h - nascer) / (por - nascer)) x (1 + ruido)

- `kWp` vem do `EnergyAsset` (inversor) do estabelecimento.
- `PR` (performance ratio) desconta perdas de temperatura, sujeira, cabos e conversao.
- `fator_do_dia` simula nebulosidade: sorteado uma vez por dia, entre `cloud_min` e 1.
- `ruido` de +-`noise_pct` por minuto simula nuvens passando - dado limpo demais entrega que e
  simulado (mesma preocupacao da curva P(t) dos carregadores, skill integracao-sems-simulador).

Todos os sorteios sao derivados de (serial, data, minuto): a mesma planta no mesmo minuto
sempre gera o mesmo valor, mesmo que o processo reinicie - reprodutivel para ensaiar a demo.

Os parametros default sao PREMISSAS DE SIMULACAO, nao medicao nem datasheet.
"""

import math
import random
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
_KW = Decimal("0.001")


@dataclass(frozen=True)
class SolarParams:
    peak_kwp: Decimal
    sunrise_hour: float = 6.0
    sunset_hour: float = 18.0
    performance_ratio: float = 0.80
    cloud_min: float = 0.55
    noise_pct: float = 0.05


def day_factor(serial: str, local_date, params: SolarParams) -> float:
    rng = random.Random(f"{serial}|{local_date.isoformat()}")
    return rng.uniform(params.cloud_min, 1.0)


def solar_power_kw(serial: str, at: datetime, params: SolarParams) -> Decimal:
    """Potencia FV (kW) entregue pelo inversor no instante `at` (aware, qualquer fuso)."""
    local = at.astimezone(LOCAL_TZ)
    hour = local.hour + local.minute / 60 + local.second / 3600
    if hour <= params.sunrise_hour or hour >= params.sunset_hour:
        return Decimal("0.000")

    position = (hour - params.sunrise_hour) / (params.sunset_hour - params.sunrise_hour)
    shape = math.sin(math.pi * position)
    minute_key = local.strftime("%Y-%m-%dT%H:%M")
    noise = random.Random(f"{serial}|{minute_key}").uniform(-params.noise_pct, params.noise_pct)

    power = (
        float(params.peak_kwp)
        * params.performance_ratio
        * day_factor(serial, local.date(), params)
        * shape
        * (1 + noise)
    )
    return Decimal(str(max(0.0, power))).quantize(_KW, rounding=ROUND_HALF_UP)
