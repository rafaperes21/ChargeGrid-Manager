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
from app.api.fleet import router as fleet_router
from app.api.health import router as health_router
from app.api.onboarding import router as onboarding_router
from app.api.plans import router as plans_router
from app.api.pricing_suggestions import router as pricing_suggestions_router
from app.api.queue import router as queue_router
from app.api.reports import router as reports_router
from app.api.reservations import router as reservations_router
from app.api.sessions import router as sessions_router
from app.api.subscriptions import router as subscriptions_router
from app.api.tariffs import router as tariffs_router
from app.api.users import router as users_router
from app.core.config import settings

logger = logging.getLogger(__name__)

# Descricoes por tag pro Swagger (/docs) agrupar de forma legivel - baixo custo, sinaliza
# prontidao pra integracao externa (Prioridade 5, Tarefa 5.4). Endpoints continuam usando o
# proprio docstring como descricao individual quando existe; isto so descreve o grupo.
TAGS_METADATA = [
    {"name": "auth", "description": "Registro, login e emissão do token JWT."},
    {
        "name": "establishments",
        "description": (
            "Cadastro de estabelecimentos: limites de precificação, coordenadas, formas de "
            "pagamento aceitas, status dos carregadores e agenda de reservas."
        ),
    },
    {
        "name": "chargers",
        "description": "Cadastro e status dos carregadores HCA G2 por estabelecimento.",
    },
    {
        "name": "plans",
        "description": (
            "Catálogo fixo de planos da plataforma - o proprietário só liga/desliga níveis, "
            "nunca define preço, desconto ou franquia."
        ),
    },
    {
        "name": "subscriptions",
        "description": (
            "Assinatura do cliente a um plano habilitado pelo estabelecimento - mesmo "
            "catálogo fixo de `plans`, o cliente só escolhe entre os níveis oferecidos."
        ),
    },
    {"name": "users", "description": "Usuários (clientes e proprietários) e bloqueio de acesso."},
    {"name": "chatbot", "description": "Assistente técnico do proprietário (Gemini + LangChain)."},
    {
        "name": "tariffs",
        "description": "Faixas de tarifa por horário local e sugestão de precificação dinâmica.",
    },
    {
        "name": "dashboard",
        "description": (
            "Visão consolidada em tempo real de um estabelecimento: potência, receita, "
            "sessões ativas e anomalias detectadas pela IA."
        ),
    },
    {
        "name": "onboarding",
        "description": (
            "Calculadora de dimensionamento elétrico do HCA G2 para novos estabelecimentos."
        ),
    },
    {
        "name": "sessions",
        "description": (
            "Ciclo de vida da sessão de carregamento: abertura por RFID, acompanhamento ao "
            "vivo, recibo digital e forma de pagamento (declarativa)."
        ),
    },
    {
        "name": "queue",
        "description": "Fila de espera por carregador, com reserva de 15 minutos ao liberar vaga.",
    },
    {
        "name": "reservations",
        "description": (
            "Reserva antecipada de horário num carregador específico, com tolerância de "
            "no-show."
        ),
    },
    {
        "name": "reports",
        "description": (
            "Fechamento financeiro por período: receita, sessões concluídas, energia total."
        ),
    },
    {
        "name": "pricing-suggestions",
        "description": "Sugestão de precificação dinâmica pela IA - nunca aplica tarifa sozinha.",
    },
    {
        "name": "fleet",
        "description": (
            "Visão agregada multi-estabelecimento, pra demonstrar a escala da plataforma."
        ),
    },
    {"name": "health", "description": "Verificação de disponibilidade do serviço."},
]


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


app = FastAPI(
    title="ChargeGrid-Manager API",
    description=(
        "API do ChargeGrid-Manager - plataforma de gestão de recarga de veículos elétricos "
        "sobre o carregador GoodWe HCA G2. Serve os portais do proprietário e do cliente."
    ),
    lifespan=lifespan,
    openapi_tags=TAGS_METADATA,
)

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
app.include_router(reports_router)
app.include_router(pricing_suggestions_router)
app.include_router(reservations_router)
app.include_router(fleet_router)
app.include_router(subscriptions_router)
