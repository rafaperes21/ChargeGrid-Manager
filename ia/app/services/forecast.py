"""Previsao de demanda por estabelecimento - Prophet sobre kWh/hora, com fallback para media
historica simples. Ver skill `ml-previsao-e-anomalias`, secao 1.

Alvo e kWh/hora (nao sessoes: `charging_sessions` de M3 nao existe ainda), derivado de
`total_energy_kwh` diferenciado por hora e somado entre os carregadores do estabelecimento.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Charger, ChargerReading
from app.schemas.forecast import BacktestSummary, ForecastResponse, HeatmapCell, PeriodMetric

LOCAL_TZ_NAME = "America/Sao_Paulo"
_WEEKDAY_NAMES_PT = (
    "segunda-feira",
    "terca-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sabado",
    "domingo",
)


def load_hourly_kwh_series(db: Session, establishment_id: uuid.UUID) -> pd.DataFrame:
    """Serie ['ds', 'y'] de kWh/hora do estabelecimento, derivada do acumulador
    `total_energy_kwh` de cada carregador. Diffs negativos (reset do acumulador) sao
    clipados em 0 - a IA nao pode "faturar" energia negativa."""
    rows = db.execute(
        select(ChargerReading.charger_id, ChargerReading.timestamp, ChargerReading.total_energy_kwh)
        .join(Charger, Charger.id == ChargerReading.charger_id)
        .where(Charger.establishment_id == establishment_id)
        .order_by(ChargerReading.charger_id, ChargerReading.timestamp)
    ).all()

    if not rows:
        return pd.DataFrame(columns=["ds", "y"])

    df = pd.DataFrame(rows, columns=["charger_id", "timestamp", "total_energy_kwh"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["total_energy_kwh"] = df["total_energy_kwh"].astype(float)
    df["hour"] = df["timestamp"].dt.floor("h")

    last_per_hour = df.groupby(["charger_id", "hour"])["total_energy_kwh"].last().reset_index()
    last_per_hour = last_per_hour.sort_values(["charger_id", "hour"])
    last_per_hour["delta_kwh"] = (
        last_per_hour.groupby("charger_id")["total_energy_kwh"].diff().clip(lower=0)
    )

    hourly = last_per_hour.groupby("hour")["delta_kwh"].sum(min_count=1).reset_index()
    hourly = hourly.rename(columns={"hour": "ds", "delta_kwh": "y"})
    hourly = hourly.dropna(subset=["y"])
    hourly["ds"] = hourly["ds"].dt.tz_localize(None)
    return hourly.sort_values("ds").reset_index(drop=True)


def has_sufficient_history(df: pd.DataFrame, min_days: int) -> bool:
    if df.empty:
        return False
    span_days = (df["ds"].max() - df["ds"].min()).total_seconds() / 86400
    return span_days >= min_days


def history_days_available(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return round((df["ds"].max() - df["ds"].min()).total_seconds() / 86400, 1)


@dataclass
class _CacheEntry:
    model: Any
    model_version: str
    trained_at: datetime
    fingerprint: tuple
    computed_at: datetime


_MODEL_CACHE: dict[uuid.UUID, _CacheEntry] = {}


def train_or_get_cached_model(
    establishment_id: uuid.UUID, df: pd.DataFrame, settings: Settings
) -> tuple[Any, str, datetime]:
    """Treina o Prophet ou reaproveita o modelo em cache - o dashboard nao pode disparar
    retreino a cada requisicao."""
    import prophet
    from prophet import Prophet

    fingerprint = (len(df), df["ds"].max())
    now = datetime.now(tz=UTC)
    cached = _MODEL_CACHE.get(establishment_id)
    if (
        cached is not None
        and cached.fingerprint == fingerprint
        and (now - cached.computed_at).total_seconds() < settings.forecast_cache_ttl_seconds
    ):
        return cached.model, cached.model_version, cached.trained_at

    model = Prophet(weekly_seasonality=True, daily_seasonality=True, yearly_seasonality=False)
    model.add_country_holidays(country_name="BR")
    model.fit(df)

    model_version = f"prophet-{prophet.__version__}-v1"
    _MODEL_CACHE[establishment_id] = _CacheEntry(model, model_version, now, fingerprint, now)
    return model, model_version, now


def forecast_next_hours(model: Any, horizon_hours: int) -> pd.DataFrame:
    future = model.make_future_dataframe(periods=horizon_hours, freq="h", include_history=False)
    forecast = model.predict(future)
    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]


def _to_local(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.tz_localize("UTC").dt.tz_convert(LOCAL_TZ_NAME)


def build_heatmap(forecast_df: pd.DataFrame) -> list[HeatmapCell]:
    local_ds = _to_local(forecast_df["ds"])
    cells = []
    for ds_local, row in zip(local_ds, forecast_df.itertuples(index=False)):
        cells.append(
            HeatmapCell(
                day_of_week=ds_local.weekday(),
                hour_local=ds_local.hour,
                predicted_kwh=max(0.0, float(row.yhat)),
                lower=max(0.0, float(row.yhat_lower)),
                upper=max(0.0, float(row.yhat_upper)),
            )
        )
    return cells


def label_peaks(forecast_df: pd.DataFrame, top_n: int = 2) -> list[str]:
    if forecast_df.empty:
        return []
    local_ds = _to_local(forecast_df["ds"])
    working = forecast_df.copy()
    working["ds_local"] = local_ds
    top = working.nlargest(top_n, "yhat")

    now_local = datetime.now(tz=UTC).astimezone(local_ds.iloc[0].tzinfo)
    labels = []
    for row in top.itertuples(index=False):
        ts_local = row.ds_local
        if ts_local.date() == now_local.date():
            day_word = "hoje"
        elif ts_local.date() == (now_local.date() + timedelta(days=1)):
            day_word = "amanha"
        else:
            day_word = _WEEKDAY_NAMES_PT[ts_local.weekday()]
        end_hour = (ts_local.hour + 1) % 24
        labels.append(f"{day_word} das {ts_local.hour}h as {end_hour}h: alta demanda esperada")
    return labels


def run_backtest(df: pd.DataFrame, model: Any) -> BacktestSummary | None:
    """Backtest com corte temporal (nunca split aleatorio - vaza futuro no treino)."""
    from prophet.diagnostics import cross_validation, performance_metrics

    span_days = (df["ds"].max() - df["ds"].min()).days
    horizon_days = 2
    initial_days = max(14, span_days - 14)
    if span_days < initial_days + horizon_days + 1:
        return None

    try:
        cv = cross_validation(
            model,
            initial=f"{initial_days} days",
            period="7 days",
            horizon=f"{horizon_days} days",
            disable_tqdm=True,
        )
        metrics = performance_metrics(cv)
    except Exception:
        return None

    overall_mae = float(metrics["mae"].mean())
    # Prophet omite a coluna 'mape' quando a janela de CV tem horas com demanda real ~0
    # (comum aqui - varias horas ociosas por dia) - MAPE fica indefinido, nao e um erro.
    overall_mape = float(metrics["mape"].mean()) if "mape" in metrics.columns else None
    return BacktestSummary(
        overall_mae=overall_mae,
        overall_mape=overall_mape,
        by_period={"geral": PeriodMetric(mae=overall_mae, mape=overall_mape)},
    )


def historical_average_fallback(df: pd.DataFrame, horizon_hours: int) -> pd.DataFrame:
    """Fallback obrigatorio: media historica por dia-da-semana/hora, quando o Prophet falha."""
    local_ds = _to_local(df["ds"])
    working = df.copy()
    working["dow"] = local_ds.dt.weekday
    working["hour"] = local_ds.dt.hour

    means = working.groupby(["dow", "hour"])["y"].mean()
    stds = working.groupby(["dow", "hour"])["y"].std().fillna(0.0)
    overall_mean = float(working["y"].mean())

    last_ts = pd.to_datetime(df["ds"]).max().tz_localize("UTC")
    future_index = pd.date_range(
        last_ts + pd.Timedelta(hours=1), periods=horizon_hours, freq="h", tz="UTC"
    )

    rows = []
    for ts in future_index:
        ts_local = ts.tz_convert(LOCAL_TZ_NAME)
        key = (ts_local.weekday(), ts_local.hour)
        mean = float(means.get(key, overall_mean))
        std = float(stds.get(key, 0.0))
        rows.append(
            {
                "ds": ts.tz_localize(None),
                "yhat": mean,
                "yhat_lower": max(0.0, mean - std),
                "yhat_upper": mean + std,
            }
        )
    return pd.DataFrame(rows)


def get_forecast(
    db: Session, establishment_id: uuid.UUID, horizon_hours: int, settings: Settings
) -> ForecastResponse:
    df = load_hourly_kwh_series(db, establishment_id)
    days_available = history_days_available(df)

    if not has_sufficient_history(df, settings.forecast_min_history_days):
        return ForecastResponse(
            establishment_id=establishment_id,
            status="insufficient_data",
            model_version=None,
            trained_at=None,
            history_days_available=days_available,
            horizon_hours=horizon_hours,
            heatmap=[],
            peak_labels=[],
            backtest=None,
            fallback_used=False,
            fallback_reason=None,
        )

    try:
        model, model_version, trained_at = train_or_get_cached_model(establishment_id, df, settings)
        forecast_df = forecast_next_hours(model, horizon_hours)
        backtest = run_backtest(df, model)
        return ForecastResponse(
            establishment_id=establishment_id,
            status="ok",
            model_version=model_version,
            trained_at=trained_at,
            history_days_available=days_available,
            horizon_hours=horizon_hours,
            heatmap=build_heatmap(forecast_df),
            peak_labels=label_peaks(forecast_df),
            backtest=backtest,
            fallback_used=False,
            fallback_reason=None,
        )
    except Exception as exc:  # fallback obrigatorio - a IA nunca pode quebrar a resposta
        fallback_df = historical_average_fallback(df, horizon_hours)
        return ForecastResponse(
            establishment_id=establishment_id,
            status="ok",
            model_version=None,
            trained_at=None,
            history_days_available=days_available,
            horizon_hours=horizon_hours,
            heatmap=build_heatmap(fallback_df),
            peak_labels=label_peaks(fallback_df),
            backtest=None,
            fallback_used=True,
            fallback_reason=str(exc),
        )
