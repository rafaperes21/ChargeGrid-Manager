"""Proxy read-only pro endpoint de sugestao de precificacao do servico de IA - mesmo padrao
de `services/dashboard._fetch_anomalies`: o frontend nunca fala direto com o `/ia`, so com o
backend principal, que repassa e tolera o `/ia` estar fora do ar.
"""

import uuid

import requests

from app.core.config import Settings
from app.schemas.pricing_suggestion import PricingSuggestionItem, PricingSuggestionsResponse


def fetch_pricing_suggestions(
    establishment_id: uuid.UUID, horizon_hours: int, settings: Settings
) -> PricingSuggestionsResponse:
    url = f"{settings.ia_service_url}/pricing-suggestions/establishments/{establishment_id}"
    try:
        # 30s, nao 10 (padrao dos outros proxies pro /ia): esse endpoint reajusta o Prophet
        # do zero a cada chamada (sem cache de modelo) - medido em ~10s so pra isso, entao o
        # timeout curto derrubava a sugestao pra "ia_unavailable" de forma intermitente
        # mesmo com o /ia no ar e respondendo, sem qualquer erro real acontecendo.
        response = requests.get(url, params={"horizon_hours": horizon_hours}, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return PricingSuggestionsResponse(
            establishment_id=establishment_id, status="ia_unavailable", suggestions=[]
        )

    data = response.json()
    suggestions = [PricingSuggestionItem(**item) for item in data.get("suggestions", [])]
    return PricingSuggestionsResponse(
        establishment_id=establishment_id,
        status=data.get("status", "ok"),
        suggestions=suggestions,
    )
