from decimal import Decimal

from pydantic import BaseModel


class FleetOverviewResponse(BaseModel):
    establishments_count: int
    chargers_count: int
    total_kwh_managed: Decimal
    total_revenue_processed: Decimal
    finished_sessions_count: int
    anomalies_detected_count: int
    ia_unavailable: bool


class FleetImpactResponse(BaseModel):
    """So os 3 numeros da tela de impacto (Tarefa 5.3) - publico, sem autenticacao."""

    establishments_count: int
    total_kwh_managed: Decimal
    total_revenue_processed: Decimal
    co2_avoided_kg: Decimal
