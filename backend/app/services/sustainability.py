"""Calculo de sustentabilidade (skill `tarifacao-e-sessoes` secao 7) - usado na tela de
impacto (Prioridade 5, Tarefa 5.3). Fatores em config (`Settings`), nunca hardcoded aqui.
"""

from decimal import Decimal

from app.core.config import Settings


def co2_avoided_kg(energy_kwh: Decimal, settings: Settings) -> Decimal:
    km_equivalentes = energy_kwh / Decimal(str(settings.avg_vehicle_kwh_per_km))
    return km_equivalentes * Decimal(str(settings.co2_emission_factor_kg_per_km))
