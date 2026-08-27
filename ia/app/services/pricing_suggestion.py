"""Sugestao de precificacao dinamica - skill `ml-previsao-e-anomalias` secao 2. Nao e um
modelo proprio: e uma regra sobre a previsao de demanda (`services/forecast.py`).

    se demanda_prevista(hora) > p80(demanda_historica daquela hora):
        sugerir tarifa x (1 + ajuste), limitado a max_increase_pct
    se demanda_prevista(hora) < p20(...):
        sugerir tarifa x (1 - ajuste), limitado a max_decrease_pct

Modo padrao e sugerir, nunca aplicar - este servico so le e devolve sugestoes, nunca escreve
em `tariff_rules`. O ajuste sugerido e sempre o limite configurado pelo proprietario
(`Establishment.max_increase_pct`/`max_decrease_pct`): a regra da skill nao define uma funcao
continua de intensidade, so o teto - aplicar o teto quando o gatilho dispara e a leitura mais
simples e mais conservadora dela.
"""

import uuid
from datetime import time
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Establishment, TariffRule
from app.schemas.pricing_suggestion import PricingSuggestionItem, PricingSuggestionResponse
from app.services.forecast import (
    get_forecast,
    has_sufficient_history,
    history_days_available,
    load_hourly_kwh_series,
)

_END_OF_DAY = time(23, 59, 59, 999999)
_START_OF_DAY = time(0, 0)
_PERCENTILE_HIGH = 0.80
_PERCENTILE_LOW = 0.20


def historical_percentiles(df: pd.DataFrame) -> dict[tuple[int, int], tuple[float, float]]:
    """p20/p80 de kWh/hora historico, por (dia da semana, hora local) - mesmo agrupamento de
    `forecast.historical_average_fallback`, mas percentis em vez de media/desvio."""
    if df.empty:
        return {}

    local_ds = (
        pd.to_datetime(df["ds"]).dt.tz_localize("UTC").dt.tz_convert("America/Sao_Paulo")
    )
    working = df.copy()
    working["dow"] = local_ds.dt.weekday
    working["hour"] = local_ds.dt.hour

    grouped = working.groupby(["dow", "hour"])["y"]
    p20 = grouped.quantile(_PERCENTILE_LOW)
    p80 = grouped.quantile(_PERCENTILE_HIGH)

    return {key: (float(p20[key]), float(p80[key])) for key in p80.index}


def _expand_to_day_intervals(
    days_of_week: str, start: time, end: time
) -> list[tuple[int, time, time]]:
    """Mesma logica de `backend/app/services/tariffs.py::_expand_to_day_intervals`, duplicada
    de proposito - servico read-only, deployado separado, nunca importa codigo do backend."""
    days = [int(d) for d in days_of_week.split(",") if d != ""]
    intervals: list[tuple[int, time, time]] = []
    for day in days:
        if end > start:
            intervals.append((day, start, end))
        else:
            intervals.append((day, start, _END_OF_DAY))
            intervals.append(((day + 1) % 7, _START_OF_DAY, end))
    return intervals


def resolve_tariff_rule_for_hour(
    rules: list[TariffRule], day_of_week: int, hour_local: int
) -> TariffRule | None:
    """Acha a regra vigente num (dia, hora) do horizonte previsto - usa o inicio da hora como
    instante representativo. Uma regra que muda de preco no meio de uma hora do heatmap
    (ex.: 18h30) nao e distinguida por hora cheia; mesma granularidade do heatmap de previsao."""
    moment = time(hour_local, 0)
    for rule in rules:
        intervals = _expand_to_day_intervals(
            rule.days_of_week, rule.start_time_local, rule.end_time_local
        )
        for day, start, end in intervals:
            if day == day_of_week and start <= moment < end:
                return rule
    return None


def _round_price(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def get_pricing_suggestions(
    db: Session, establishment_id: uuid.UUID, horizon_hours: int, settings: Settings
) -> PricingSuggestionResponse:
    establishment = db.get(Establishment, establishment_id)
    max_increase_pct = establishment.max_increase_pct
    max_decrease_pct = establishment.max_decrease_pct

    df = load_hourly_kwh_series(db, establishment_id)
    days_available = history_days_available(df)

    if not has_sufficient_history(df, settings.forecast_min_history_days):
        return PricingSuggestionResponse(
            establishment_id=establishment_id,
            status="insufficient_data",
            history_days_available=days_available,
            horizon_hours=horizon_hours,
            max_increase_pct=max_increase_pct,
            max_decrease_pct=max_decrease_pct,
            suggestions=[],
        )

    percentiles = historical_percentiles(df)
    forecast = get_forecast(db, establishment_id, horizon_hours, settings)
    rules = list(establishment.tariff_rules)

    suggestions: list[PricingSuggestionItem] = []
    for cell in forecast.heatmap:
        bucket = percentiles.get((cell.day_of_week, cell.hour_local))
        if bucket is None:
            continue
        p20, p80 = bucket

        if cell.predicted_kwh > p80:
            direction, threshold, adjustment_pct = "increase", p80, max_increase_pct
        elif cell.predicted_kwh < p20:
            direction, threshold, adjustment_pct = "decrease", p20, max_decrease_pct
        else:
            continue

        rule = resolve_tariff_rule_for_hour(rules, cell.day_of_week, cell.hour_local)
        if rule is None:
            continue

        signed_pct = adjustment_pct if direction == "increase" else -adjustment_pct
        factor = Decimal("1") + (signed_pct / Decimal("100"))
        suggested_price = _round_price(rule.price_per_kwh * factor)
        reason = (
            f"previsao de {cell.predicted_kwh:.2f} kWh acima do p80 historico "
            f"({threshold:.2f} kWh) para este horario"
            if direction == "increase"
            else (
                f"previsao de {cell.predicted_kwh:.2f} kWh abaixo do p20 historico "
                f"({threshold:.2f} kWh) para este horario"
            )
        )

        suggestions.append(
            PricingSuggestionItem(
                day_of_week=cell.day_of_week,
                hour_local=cell.hour_local,
                predicted_kwh=cell.predicted_kwh,
                threshold_kwh=threshold,
                direction=direction,
                tariff_rule_id=rule.id,
                tariff_rule_name=rule.name,
                current_price_per_kwh=rule.price_per_kwh,
                suggested_price_per_kwh=suggested_price,
                adjustment_pct=adjustment_pct,
                reason=reason,
            )
        )

    return PricingSuggestionResponse(
        establishment_id=establishment_id,
        status="ok",
        history_days_available=days_available,
        horizon_hours=horizon_hours,
        max_increase_pct=max_increase_pct,
        max_decrease_pct=max_decrease_pct,
        suggestions=suggestions,
    )
