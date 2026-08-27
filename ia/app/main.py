from fastapi import FastAPI

from app.api.anomalies import router as anomalies_router
from app.api.forecast import router as forecast_router
from app.api.health import router as health_router
from app.api.pricing_suggestions import router as pricing_suggestions_router

app = FastAPI(title="ChargeGrid-Manager IA")

app.include_router(health_router)
app.include_router(anomalies_router)
app.include_router(forecast_router)
app.include_router(pricing_suggestions_router)
