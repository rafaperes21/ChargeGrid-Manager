from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://chargegrid:chargegrid@localhost:5432/chargegrid"

    # TODO(seguranca): trocar por segredo forte via variavel de ambiente antes de qualquer deploy.
    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    google_oauth_client_id: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
