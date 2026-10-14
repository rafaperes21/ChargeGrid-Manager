"""Visao da "sessao em andamento" do cliente - extraida de `api/sessions.py` (Sprint 4) para
ser a mesma fonte do endpoint `GET /sessions/current` e da ferramenta do assistente do cliente
(`services/chatbot_customer.py`). Dois caminhos calculando a mesma coisa divergem.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import ChargingSessionStatus
from app.models.session import ChargingSession
from app.models.user import User
from app.services.dashboard import latest_reading
from app.services.sessions import estimate_live_amount, sync_session
from app.services.vehicle_battery import estimate_battery_status


@dataclass
class CurrentSessionSnapshot:
    session: ChargingSession
    estimated_amount_due: Decimal | None
    battery_pct_estimate: Decimal | None
    estimated_minutes_remaining: int | None


def get_current_session_snapshot(db: Session, user: User) -> CurrentSessionSnapshot | None:
    """Sessao pending/active do usuario, ja sincronizada com as leituras. `None` se nao houver
    - inclusive quando o `sync_session` desta chamada acabou de fechar a sessao (o contrato e
    "pending/active ou nada", nunca vazar status terminal)."""
    session = (
        db.query(ChargingSession)
        .filter(
            ChargingSession.user_id == user.id,
            ChargingSession.status.in_(
                [ChargingSessionStatus.pending, ChargingSessionStatus.active]
            ),
        )
        .first()
    )
    if session is None:
        return None
    session = sync_session(db, session)
    if session.status not in (ChargingSessionStatus.pending, ChargingSessionStatus.active):
        return None

    amount = battery_pct = minutes = None
    if session.status == ChargingSessionStatus.active:
        amount = estimate_live_amount(db, session, datetime.now(tz=UTC))
        reading = latest_reading(db, session.charger_id)
        battery_pct, minutes = estimate_battery_status(
            vehicle_model=user.vehicle_model,
            energy_kwh=session.energy_kwh,
            current_power_kw=reading.power_kw if reading else None,
        )
    return CurrentSessionSnapshot(session, amount, battery_pct, minutes)
