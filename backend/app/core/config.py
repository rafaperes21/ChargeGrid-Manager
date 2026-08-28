from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://chargegrid:chargegrid@localhost:5432/chargegrid"

    # TODO(seguranca): trocar por segredo forte via variavel de ambiente antes de qualquer deploy.
    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    google_oauth_client_id: str = ""

    # Origens do frontend liberadas no CORS - lista separada por virgula, nao JSON, para
    # ficar simples de editar no .env. `localhost` e `127.0.0.1` sao origens *diferentes*
    # pro CORSMiddleware mesmo apontando pro mesmo servidor - sem as duas variantes, quem
    # abrir o frontend por IP em vez de nome (comum em navegador/SO configurado diferente)
    # toma "Disallowed CORS origin" (400) bem no preflight do login, silenciosamente.
    cors_allowed_origins: str = (
        "http://localhost:5173,http://localhost:5174,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174"
    )

    # Chatbot do proprietario (M7 minimo) - LLM local via Ollama, sem chave de API.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ia_service_url: str = "http://localhost:8001"

    # Integracao SEMS+ (M2) - trocar "simulator" por "real" (quando o RealSemsClient sair do
    # stub) nao deve exigir mudar nada fora de app/integracoes/.
    sems_source: str = "simulator"
    poll_interval_seconds: int = 60
    # Task assincrona no startup do FastAPI so roda se isto for true - default false pra nao
    # rodar durante os testes (TestClient importa app.main) nem em ambientes sem Postgres de pe.
    polling_enabled: bool = False
    polling_offline_after_failures: int = 3

    # Sustentabilidade (skill tarifacao-e-sessoes §7) - em config, nao hardcoded, porque a
    # matriz eletrica brasileira muda e o numero precisa ser defensavel. Usado na tela de
    # impacto (Prioridade 5, Tarefa 5.3).
    avg_vehicle_kwh_per_km: float = 0.16
    co2_emission_factor_kg_per_km: float = 0.12

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
