"""Motor da curva P(t) de uma sessao de carregamento AC, seguindo a atividade 5.

Fases: rampa (0-2 min, sobe ate a potencia negociada) -> plato (constante, com ruido
gaussiano +-2%) -> taper (80-100% do SoC, decaimento ate ~10% da nominal) -> fim (cai a
zero). Ver skill `integracao-sems-simulador`, secao 4.

O plato e limitado pelo menor entre a potencia nominal do carregador e o OBC do veiculo -
o gargalo costuma ser o carro, nao o carregador (`vehicles.py`).
"""

import random
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import ChargerStatus
from simulador.vehicles import VehicleProfile

RAMP_DURATION = timedelta(minutes=2)
TAPER_SOC_START_PCT = Decimal("0.80")
TAPER_END_POWER_PCT_OF_NOMINAL = Decimal("0.10")
PLATEAU_NOISE_STD_PCT = Decimal("0.02")
# Clipado abaixo da tolerancia de medicao da regra `over_nominal_power` (5%, ver
# `ia/app/core/config.py`) - senao o ruido "normal" do plato dispara falso positivo sempre
# que o carro tem OBC igual a nominal do carregador (comum no catalogo de veiculos).
PLATEAU_NOISE_CLIP_PCT = Decimal("0.04")
TAPER_NOISE_STD_PCT = Decimal("0.01")

_POWER_QUANTIZE = Decimal("0.001")


@dataclass
class CurveSample:
    offset: timedelta
    power_kw: Decimal
    status: ChargerStatus
    error_code: str | None = None


def _quantize_power(power_kw: Decimal) -> Decimal:
    if power_kw < 0:
        power_kw = Decimal("0")
    return power_kw.quantize(_POWER_QUANTIZE, rounding=ROUND_HALF_UP)


def plateau_power_kw(charger_nominal_kw: Decimal, vehicle: VehicleProfile) -> Decimal:
    """O gargalo e o veiculo, nao o carregador: min(nominal do charger, OBC do carro)."""
    return min(charger_nominal_kw, vehicle.obc_max_kw)


def generate_session_samples(
    charger_nominal_kw: Decimal,
    vehicle: VehicleProfile,
    initial_soc_pct: Decimal,
    target_soc_pct: Decimal,
    rng: random.Random,
    fine_interval: timedelta = timedelta(minutes=1),
) -> list[CurveSample]:
    """Gera as amostras de uma sessao completa, com offsets relativos ao inicio dela."""
    plateau_kw = plateau_power_kw(charger_nominal_kw, vehicle)
    samples: list[CurveSample] = []
    cursor = timedelta(0)

    ramp_steps = max(1, round(RAMP_DURATION / fine_interval))
    for i in range(1, ramp_steps + 1):
        offset = fine_interval * i
        power = plateau_kw * Decimal(i) / Decimal(ramp_steps)
        samples.append(CurveSample(offset, _quantize_power(power), ChargerStatus.carregando))
    cursor = fine_interval * ramp_steps

    has_plateau = initial_soc_pct < TAPER_SOC_START_PCT
    if has_plateau:
        plateau_energy_kwh = vehicle.battery_capacity_kwh * (TAPER_SOC_START_PCT - initial_soc_pct)
        plateau_duration = timedelta(hours=float(plateau_energy_kwh / plateau_kw))
        steps = max(1, round(plateau_duration / fine_interval))
        for i in range(1, steps + 1):
            offset = cursor + fine_interval * i
            noise_pct = Decimal(str(rng.gauss(0, float(PLATEAU_NOISE_STD_PCT))))
            noise_pct = max(-PLATEAU_NOISE_CLIP_PCT, min(PLATEAU_NOISE_CLIP_PCT, noise_pct))
            power = plateau_kw * (Decimal("1") + noise_pct)
            samples.append(CurveSample(offset, _quantize_power(power), ChargerStatus.carregando))
        cursor += fine_interval * steps

    has_taper = target_soc_pct > TAPER_SOC_START_PCT
    if has_taper:
        taper_end_kw = charger_nominal_kw * TAPER_END_POWER_PCT_OF_NOMINAL
        taper_energy_kwh = vehicle.battery_capacity_kwh * (target_soc_pct - TAPER_SOC_START_PCT)
        avg_taper_power = (plateau_kw + taper_end_kw) / Decimal("2")
        taper_duration = timedelta(hours=float(taper_energy_kwh / avg_taper_power))
        steps = max(1, round(taper_duration / fine_interval))
        for i in range(1, steps + 1):
            offset = cursor + fine_interval * i
            fraction = Decimal(i) / Decimal(steps)
            power = plateau_kw - (plateau_kw - taper_end_kw) * fraction
            noise_pct = Decimal(str(rng.gauss(0, float(TAPER_NOISE_STD_PCT))))
            power *= Decimal("1") + noise_pct
            samples.append(CurveSample(offset, _quantize_power(power), ChargerStatus.carregando))
        cursor += fine_interval * steps

    # amostra final um intervalo depois da ultima leitura de carregamento - o proximo poll
    # ve o carro ja desconectado. Garante timestamp estritamente maior que o anterior.
    samples.append(CurveSample(cursor + fine_interval, Decimal("0.000"), ChargerStatus.livre))
    return samples


def generate_idle_samples(
    start: datetime, end: datetime, interval: timedelta
) -> Iterator[tuple[datetime, Decimal, ChargerStatus]]:
    """Leituras de um carregador sem carro conectado: potencia zero, status livre.

    Comeca em `start + interval`, nunca em `start` - o chamador trata `start` como o ultimo
    instante ja emitido (fim da sessao anterior ou inicio da janela), nao um novo ponto."""
    cursor = start + interval
    while cursor < end:
        yield cursor, Decimal("0.000"), ChargerStatus.livre
        cursor += interval
