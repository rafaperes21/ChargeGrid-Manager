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
from app.api.tariffs import router as tariffs_router
from app.api.users import router as users_router
from app.core.config import settings

app = FastAPI(title="ChargeGrid-Manager API")

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
