from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracao do microservico de IA. Conexao ao MESMO Postgres do backend, em modo
    leitura - ver `app/db/session.py`. Nunca escreve em tabela transacional."""

    database_url: str = "postgresql+psycopg://chargegrid:chargegrid@localhost:5432/chargegrid"

    # Previsao de demanda (Prophet)
    forecast_min_history_days: int = 28
    forecast_default_horizon_hours: int = 48
    forecast_cache_ttl_seconds: int = 3600

    # Deteccao de anomalias
    anomaly_default_lookback_hours: int = 168
    anomaly_zero_power_minutes: int = 30
    anomaly_over_nominal_tolerance_pct: Decimal = Decimal("0.05")
    anomaly_offline_cycles: int = 3
    anomaly_offline_cycle_minutes: int = 15

    model_dir: str = "models"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())


settings = Settings()
