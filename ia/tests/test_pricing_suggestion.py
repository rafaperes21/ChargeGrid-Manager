import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

import pandas as pd

from app.core.config import Settings
from app.models import Establishment, TariffRule
from app.schemas.forecast import ForecastResponse, HeatmapCell
from app.services.pricing_suggestion import (
    get_pricing_suggestions,
    historical_percentiles,
    resolve_tariff_rule_for_hour,
)


def _rule(
    days_of_week: str, start: time, end: time, price: str = "1.0000", is_special: bool = False
) -> TariffRule:
    return TariffRule(
        id=uuid.uuid4(),
        establishment_id=uuid.uuid4(),
        name="Faixa teste",
        days_of_week=days_of_week,
        start_time_local=start,
        end_time_local=end,
        price_per_kwh=Decimal(price),
        is_special=is_special,
    )


def test_resolve_tariff_rule_for_hour_within_simple_range():
    rule = _rule("0,1,2,3,4", time(8, 0), time(20, 0))
    assert resolve_tariff_rule_for_hour([rule], day_of_week=0, hour_local=10) is rule
    assert resolve_tariff_rule_for_hour([rule], day_of_week=0, hour_local=21) is None
    assert resolve_tariff_rule_for_hour([rule], day_of_week=5, hour_local=10) is None


def test_resolve_tariff_rule_for_hour_crossing_midnight():
    rule = _rule("0", time(22, 0), time(6, 0))
    assert resolve_tariff_rule_for_hour([rule], day_of_week=0, hour_local=23) is rule
    assert resolve_tariff_rule_for_hour([rule], day_of_week=1, hour_local=2) is rule
    assert resolve_tariff_rule_for_hour([rule], day_of_week=1, hour_local=10) is None


def test_resolve_tariff_rule_for_hour_prefere_especial_sobreposta():
    """Mesmo criterio de precedencia de `backend/app/services/tariffs.py` - uma faixa
    especial sobreposta a uma padrao sempre vence, so dentro da propria janela."""
    regular = _rule("0,1,2,3,4,5,6", time(0, 0), time(23, 59, 59))
    special = _rule("4", time(18, 0), time(19, 0), price="2.4000", is_special=True)

    assert resolve_tariff_rule_for_hour([regular, special], day_of_week=4, hour_local=18) is special
    assert resolve_tariff_rule_for_hour([regular, special], day_of_week=4, hour_local=20) is regular
    assert resolve_tariff_rule_for_hour([regular, special], day_of_week=5, hour_local=18) is regular


def _hourly_series_with_bucket_values(
    base_date: datetime, weeks: int, bucket_values: dict
) -> pd.DataFrame:
    """Serie horaria de `weeks` semanas onde cada (dow, hour) **local** em `bucket_values`
    recebe uma lista fixa de valores repetida a cada semana - da controle exato sobre o
    p20/p80 de cada bucket sem depender de aleatoriedade. `ds` e gravado como instante UTC
    (naive), igual ao contrato real de `load_hourly_kwh_series` - `historical_percentiles`
    e quem converte de volta pra local."""
    rows = []
    for week in range(weeks):
        for (dow, hour), values in bucket_values.items():
            day_offset = week * 7 + dow
            local_day = base_date + timedelta(days=day_offset)
            local_ts = pd.Timestamp(local_day.replace(hour=hour, minute=0, second=0, microsecond=0))
            local_ts = local_ts.tz_localize("America/Sao_Paulo")
            utc_ts = local_ts.tz_convert("UTC").tz_localize(None)
            value = values[week % len(values)]
            rows.append({"ds": utc_ts, "y": value})
    return pd.DataFrame(rows).sort_values("ds").reset_index(drop=True)


def test_historical_percentiles_by_dow_hour():
    base = datetime(2026, 1, 5)  # segunda-feira, horario local (naive)
    df = _hourly_series_with_bucket_values(
        base, weeks=5, bucket_values={(0, 18): [10.0, 20.0, 30.0, 40.0, 50.0]}
    )

    percentiles = historical_percentiles(df)

    p20, p80 = percentiles[(0, 18)]
    assert p20 == pd.Series([10.0, 20.0, 30.0, 40.0, 50.0]).quantile(0.20)
    assert p80 == pd.Series([10.0, 20.0, 30.0, 40.0, 50.0]).quantile(0.80)


def _make_establishment(db_session, max_increase="20.00", max_decrease="20.00") -> Establishment:
    establishment = Establishment(
        id=uuid.uuid4(),
        name="Estacionamento Precificacao",
        kind="estacionamento",
        max_increase_pct=Decimal(max_increase),
        max_decrease_pct=Decimal(max_decrease),
    )
    db_session.add(establishment)
    db_session.flush()
    return establishment


def test_get_pricing_suggestions_returns_insufficient_data_below_minimum_history(db_session):
    establishment = _make_establishment(db_session)
    settings = Settings(forecast_min_history_days=28)
    short_df = pd.DataFrame({"ds": [datetime(2026, 1, 1)], "y": [5.0]})

    with patch(
        "app.services.pricing_suggestion.load_hourly_kwh_series", return_value=short_df
    ), patch("app.services.pricing_suggestion.get_forecast") as mock_get_forecast:
        response = get_pricing_suggestions(
            db_session, establishment.id, horizon_hours=48, settings=settings
        )

    mock_get_forecast.assert_not_called()
    assert response.status == "insufficient_data"
    assert response.suggestions == []


def test_get_pricing_suggestions_flags_increase_and_decrease(db_session):
    establishment = _make_establishment(db_session, max_increase="15.00", max_decrease="10.00")
    rule = TariffRule(
        id=uuid.uuid4(),
        establishment_id=establishment.id,
        name="Diurna",
        days_of_week="0,1,2,3,4,5,6",
        start_time_local=time(0, 0),
        end_time_local=time(23, 59, 59),
        price_per_kwh=Decimal("1.0000"),
        is_special=False,
    )
    db_session.add(rule)
    db_session.commit()

    base = datetime(2026, 1, 5)  # segunda-feira, horario local (naive)
    long_history = _hourly_series_with_bucket_values(
        base,
        weeks=5,
        bucket_values={
            (0, 18): [10.0, 20.0, 30.0, 40.0, 50.0],  # p80 ~ 46
            (0, 3): [10.0, 20.0, 30.0, 40.0, 50.0],  # p20 ~ 14
        },
    )
    settings = Settings(forecast_min_history_days=28)
    canned_forecast = ForecastResponse(
        establishment_id=establishment.id,
        status="ok",
        model_version="test-v1",
        trained_at=datetime.now(tz=UTC),
        history_days_available=35.0,
        horizon_hours=48,
        heatmap=[
            HeatmapCell(day_of_week=0, hour_local=18, predicted_kwh=90.0, lower=80.0, upper=100.0),
            HeatmapCell(day_of_week=0, hour_local=3, predicted_kwh=1.0, lower=0.0, upper=2.0),
            HeatmapCell(day_of_week=0, hour_local=12, predicted_kwh=25.0, lower=20.0, upper=30.0),
        ],
        peak_labels=[],
        backtest=None,
        fallback_used=False,
        fallback_reason=None,
    )

    with patch(
        "app.services.pricing_suggestion.load_hourly_kwh_series", return_value=long_history
    ), patch(
        "app.services.pricing_suggestion.get_forecast", return_value=canned_forecast
    ):
        response = get_pricing_suggestions(
            db_session, establishment.id, horizon_hours=48, settings=settings
        )

    assert response.status == "ok"
    by_hour = {item.hour_local: item for item in response.suggestions}

    assert by_hour[18].direction == "increase"
    assert by_hour[18].suggested_price_per_kwh == Decimal("1.1500")
    assert by_hour[18].tariff_rule_id == rule.id

    assert by_hour[3].direction == "decrease"
    assert by_hour[3].suggested_price_per_kwh == Decimal("0.9000")

    # hora 12 nao cruza p20 nem p80 do seu proprio bucket (sem historico) - sem sugestao
    assert 12 not in by_hour
