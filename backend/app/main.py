from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.chargers import router as chargers_router
from app.api.establishments import router as establishments_router
from app.api.health import router as health_router
from app.api.plans import router as plans_router
from app.api.users import router as users_router

app = FastAPI(title="ChargeGrid-Manager API")

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(establishments_router)
app.include_router(chargers_router)
app.include_router(plans_router)
app.include_router(users_router)
