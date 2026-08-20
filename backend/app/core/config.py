from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://chargegrid:chargegrid@localhost:5432/chargegrid"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
