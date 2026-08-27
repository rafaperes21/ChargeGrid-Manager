"""Visao agregada multi-estabelecimento (Prioridade 5, Tarefa 5.1/5.3) - "para fins de
demonstracao", sem trocar a arquitetura multi-tenant existente (cada estabelecimento
continua isolado em toda outra rota). So numeros somados entram aqui, nunca o nome ou o
detalhe de um estabelecimento especifico, pra nao vazar dado competitivo entre dois donos
diferentes que usam a mesma instancia.

Regra do proprio pedido: nunca inventar numero. Se a base de demonstracao tiver poucos
estabelecimentos, o numero aparece pequeno mesmo - quem le decide se e cedo pra tirar
conclusao de escala, a tela nao finge um volume que nao existe.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.charger import Charger
from app.models.enums import ChargingSessionStatus
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.schemas.fleet import FleetImpactResponse, FleetOverviewResponse
from app.services.dashboard import fetch_anomalies
from app.services.sustainability import co2_avoided_kg


def _finished_sessions_totals(db: Session) -> tuple[Decimal, Decimal, int]:
    finished = (
        db.query(ChargingSession)
        .filter(ChargingSession.status == ChargingSessionStatus.finished)
        .all()
    )
    energy_total = Decimal("0.000")
    revenue_total = Decimal("0.0000")
    for session in finished:
        energy_total += session.energy_kwh or Decimal("0.000")
        revenue_total += session.amount_due or Decimal("0.0000")
    return energy_total, revenue_total, len(finished)


def get_fleet_overview(db: Session, settings: Settings) -> FleetOverviewResponse:
    establishment_ids = [row[0] for row in db.query(Establishment.id).all()]
    establishments_count = len(establishment_ids)
    chargers_count = db.query(Charger).count()
    energy_total, revenue_total, finished_count = _finished_sessions_totals(db)

    anomalies_count = 0
    ia_unavailable = False
    for establishment_id in establishment_ids:
        anomalies, unavailable = fetch_anomalies(establishment_id, settings)
        anomalies_count += len(anomalies)
        ia_unavailable = ia_unavailable or unavailable

    return FleetOverviewResponse(
        establishments_count=establishments_count,
        chargers_count=chargers_count,
        total_kwh_managed=energy_total,
        total_revenue_processed=revenue_total,
        finished_sessions_count=finished_count,
        anomalies_detected_count=anomalies_count,
        ia_unavailable=ia_unavailable,
    )


def get_fleet_impact(db: Session, settings: Settings) -> FleetImpactResponse:
    """Subconjunto publico (sem autenticacao) do overview - so os 3 numeros de impacto da
    tela hero (Tarefa 5.3), nunca a receita quebrada por estabelecimento."""
    establishments_count = db.query(Establishment).count()
    energy_total, revenue_total, _ = _finished_sessions_totals(db)

    return FleetImpactResponse(
        establishments_count=establishments_count,
        total_kwh_managed=energy_total,
        total_revenue_processed=revenue_total,
        co2_avoided_kg=co2_avoided_kg(energy_total, settings),
    )
