"""Injetores de cenarios de anomalia sobre uma sessao de carregamento "limpa".

Cada funcao recebe as amostras geradas por `curve_engine.generate_session_samples` e devolve
uma copia modificada - a curva original fica intacta, o que mantem cada injetor testavel de
forma independente. Ver skill `integracao-sems-simulador`, secao 5, e
`ml-previsao-e-anomalias`, secao 3, para as regras que estes cenarios devem disparar.

Offline prolongado nao tem injetor aqui: e tratado no orquestrador
(`historical_generator.py`), que omite leituras num trecho - silencio, como um poll que
realmente falhou, em vez de escrever um status que o device nao se auto-reportaria.
"""

import random
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal

from simulador.curve_engine import CurveSample

ZERO_POWER_ERROR_CODE = "ERR_ZERO_POWER"
OVER_NOMINAL_ERROR_CODE = "ERR_OVER_NOMINAL"


def inject_zero_power_stall(
    samples: list[CurveSample],
    rng: random.Random,
    min_minutes: int = 35,
    max_minutes: int = 90,
) -> list[CurveSample]:
    """Zera a potencia por um trecho continuo do plato, mantendo status=carregando -
    o veiculo permanece fisicamente conectado do ponto de vista do device."""
    samples = deepcopy(samples)
    duration_minutes = rng.randint(min_minutes, max_minutes)

    candidate_indexes = [i for i, s in enumerate(samples) if s.power_kw > 0]
    if not candidate_indexes:
        return samples

    start_index = rng.choice(candidate_indexes)
    start_offset = samples[start_index].offset
    end_offset = start_offset + timedelta(minutes=duration_minutes)

    for sample in samples:
        if start_offset <= sample.offset < end_offset and sample.power_kw > 0:
            sample.power_kw = Decimal("0.000")
            sample.error_code = ZERO_POWER_ERROR_CODE
    return samples


def inject_over_nominal_spike(
    samples: list[CurveSample],
    charger_nominal_kw: Decimal,
    rng: random.Random,
    factor_range: tuple[float, float] = (1.10, 1.25),
    duration_minutes_range: tuple[int, int] = (5, 15),
) -> list[CurveSample]:
    """Multiplica a potencia acima da nominal por um trecho curto - erro de medicao/defeito."""
    samples = deepcopy(samples)
    factor = Decimal(str(rng.uniform(*factor_range)))
    duration_minutes = rng.randint(*duration_minutes_range)

    candidate_indexes = [i for i, s in enumerate(samples) if s.power_kw > 0]
    if not candidate_indexes:
        return samples

    start_index = rng.choice(candidate_indexes)
    start_offset = samples[start_index].offset
    end_offset = start_offset + timedelta(minutes=duration_minutes)

    for sample in samples:
        if start_offset <= sample.offset < end_offset and sample.power_kw > 0:
            spiked = (charger_nominal_kw * factor).quantize(Decimal("0.001"))
            sample.power_kw = max(sample.power_kw, spiked)
            sample.error_code = OVER_NOMINAL_ERROR_CODE
    return samples


def energy_reset_drop(
    running_total_kwh: Decimal,
    rng: random.Random,
    drop_fraction_range: tuple[float, float] = (0.3, 0.6),
) -> Decimal:
    """Novo total_energy_kwh menor que o anterior - reset/corrupcao do acumulador do device."""
    drop_fraction = Decimal(str(rng.uniform(*drop_fraction_range)))
    return (running_total_kwh * (Decimal("1") - drop_fraction)).quantize(Decimal("0.001"))
