import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pandas as pd

from app.core.config import Settings
from app.services.forecast import get_forecast, has_sufficient_history


def _hourly_series(days: int) -> pd.DataFrame:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    hours = days * 24
    index = pd.date_range(start, periods=hours, freq="h", tz=None)
    return pd.DataFrame({"ds": index, "y": [1.0] * hours})


def test_ten_days_of_history_is_insufficient():
    assert has_sufficient_history(_hourly_series(10), min_days=28) is False


def test_thirty_days_of_history_is_sufficient():
    assert has_sufficient_history(_hourly_series(30), min_days=28) is True


def test_empty_history_is_insufficient():
    assert has_sufficient_history(pd.DataFrame(columns=["ds", "y"]), min_days=28) is False


def test_get_forecast_short_circuits_before_training_the_model():
    """Abaixo do minimo, `get_forecast` nunca deve chamar o Prophet - so `insufficient_data`."""
    settings = Settings(forecast_min_history_days=28)
    establishment_id = uuid.uuid4()

    with patch(
        "app.services.forecast.load_hourly_kwh_series", return_value=_hourly_series(10)
    ), patch("app.services.forecast.train_or_get_cached_model") as mock_train:
        response = get_forecast(
            db=None, establishment_id=establishment_id, horizon_hours=48, settings=settings
        )

    mock_train.assert_not_called()
    assert response.status == "insufficient_data"
    assert response.heatmap == []
    assert response.model_version is None
