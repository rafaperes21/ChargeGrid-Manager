"""Assinatura de plano pelo cliente (catalogo fixo, M3 Tarefa 4.1 - skill `tarifacao-e-sessoes`
secao 4). O cliente so escolhe entre os niveis que o estabelecimento habilitou (`Plan.enabled`),
nunca define valor - mesmo catalogo fixo que o proprietario usa em `/plans`.

Ciclo de faturamento comeca no dia 1 do mes corrente (horario local), sem data de termino -
mesmo padrao ja usado em `seed_demo_history.py`. Nao ha job de renovacao/corte automatico de
ciclo (fora de escopo, mesmo criterio de outras partes do projeto sem worker em background).
"""

import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import PlanKind
from app.models.tariff import Plan
from app.models.user import Subscription, User

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")


def list_enabled_plans(db: Session, establishment_id: uuid.UUID) -> list[Plan]:
    return (
        db.query(Plan)
        .filter(Plan.establishment_id == establishment_id, Plan.enabled.is_(True))
        .order_by(Plan.kind)
        .all()
    )


def get_active_subscription(
    db: Session, user_id: uuid.UUID, establishment_id: uuid.UUID
) -> Subscription | None:
    return (
        db.query(Subscription)
        .join(Plan, Subscription.plan_id == Plan.id)
        .filter(
            Subscription.user_id == user_id,
            Subscription.active.is_(True),
            Plan.establishment_id == establishment_id,
        )
        .first()
    )


def subscribe(db: Session, user: User, plan_id: uuid.UUID) -> Subscription | None:
    """Troca a assinatura ativa do cliente pro plano escolhido - desativa qualquer assinatura
    anterior no mesmo estabelecimento (uma ativa por vez, mesmo criterio que
    `services/sessions._resolve_plan_context` ja assume ao consultar so a primeira ativa).

    Escolher `avulso` so desativa a assinatura atual e devolve `None` - nao existe linha de
    `Subscription` pra avulso porque nao ha nada pra rastrear (sem franquia, sem desconto,
    sem ciclo); "sem assinatura ativa" ja *e* avulso (skill tarifacao-e-sessoes secao 4)."""
    plan = db.get(Plan, plan_id)
    if plan is None or not plan.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano nao encontrado")

    current = get_active_subscription(db, user.id, plan.establishment_id)
    if current is not None:
        current.active = False

    if plan.kind == PlanKind.avulso:
        db.commit()
        return None

    cycle_start = datetime.now(UTC).astimezone(LOCAL_TZ).date().replace(day=1)
    subscription = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        billing_cycle_start=cycle_start,
        billing_cycle_end=None,
        active=True,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription
