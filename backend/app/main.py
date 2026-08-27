import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chargers import router as chargers_router
from app.api.chatbot import router as chatbot_router
from app.api.dashboard import router as dashboard_router
from app.api.establishments import router as establishments_router
from app.api.health import router as health_router
from app.api.onboarding import router as onboarding_router
from app.api.plans import router as plans_router
from app.api.queue import router as queue_router
from app.api.sessions import router as sessions_router
from app.api.tariffs import router as tariffs_router
from app.api.users import router as users_router
from app.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """So sobe o polling (M2) junto do processo web se POLLING_ENABLED=true - default
    false, pra dev/producao poderem preferir rodar `python -m app.integracoes.polling`
    como worker separado (skill integracao-sems-simulador, secao 3). TestClient(app) sem
    `with` nao dispara lifespan nesta versao do Starlette, entao os testes nunca sobem isto
    de qualquer forma - mas manter o default false evita surpresa se isso mudar."""
    task: asyncio.Task | None = None
    if settings.polling_enabled:
        from app.integracoes.polling import PollingService
        from app.integracoes.sems_client import get_sems_client

        service = PollingService(get_sems_client())
        task = asyncio.create_task(service.run_forever())
        logger.info("Polling (M2) iniciado junto do FastAPI")

    yield

    if task is not None:
        task.cancel()


app = FastAPI(title="ChargeGrid-Manager API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(establishments_router)
app.include_router(chargers_router)
app.include_router(plans_router)
app.include_router(users_router)
app.include_router(chatbot_router)
app.include_router(tariffs_router)
app.include_router(dashboard_router)
app.include_router(onboarding_router)
app.include_router(sessions_router)
app.include_router(queue_router)
