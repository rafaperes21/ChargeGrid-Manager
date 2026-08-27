"""Catalogo fixo de planos definido pela plataforma (M3, Tarefa 4.1) - decisao alinhada com
o professor da disciplina em 27/08/2026, desbloqueando o que `M3-tarifacao-sessoes.md`
documentava como "em espera" (ver skill `tarifacao-e-sessoes` secao 4, fonte dos valores
abaixo). O proprietario nunca define preco/desconto/franquia por conta propria - so escolhe
quais niveis deste catalogo oferece (`Plan.enabled`), nunca os valores.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import PlanKind
from app.models.tariff import Plan
from app.schemas.plan import PlanRead


@dataclass(frozen=True)
class PlanTier:
    name: str
    price: Decimal | None
    free_kwh_allowance: Decimal | None
    discount_pct: Decimal
    priority: int


PLAN_CATALOG: dict[PlanKind, PlanTier] = {
    PlanKind.avulso: PlanTier(
        name="Avulso",
        price=None,
        free_kwh_allowance=None,
        discount_pct=Decimal("0.00"),
        priority=0,
    ),
    PlanKind.mensal: PlanTier(
        name="Mensal",
        price=Decimal("149.9000"),
        free_kwh_allowance=Decimal("50.000"),
        discount_pct=Decimal("15.00"),
        priority=1,
    ),
    PlanKind.trimestral: PlanTier(
        name="Trimestral",
        price=Decimal("399.9000"),
        free_kwh_allowance=Decimal("180.000"),
        discount_pct=Decimal("25.00"),
        priority=2,
    ),
}


def get_tier(kind: PlanKind) -> PlanTier:
    return PLAN_CATALOG[kind]


def plan_to_read(plan: Plan) -> PlanRead:
    tier = get_tier(plan.kind)
    return PlanRead(
        id=plan.id,
        establishment_id=plan.establishment_id,
        kind=plan.kind,
        enabled=plan.enabled,
        name=tier.name,
        price=tier.price,
        free_kwh_allowance=tier.free_kwh_allowance,
        discount_pct=tier.discount_pct,
        priority=tier.priority,
    )


def provision_plans_for_establishment(db: Session, establishment_id: uuid.UUID) -> None:
    """Garante uma linha de `Plan` por nivel do catalogo pra este estabelecimento - chamado
    na criacao do estabelecimento. `avulso` vem habilitado por padrao (tier gratuito
    implicito); `mensal`/`trimestral` comecam desabilitados, o proprietario decide se
    oferece (skill tarifacao-e-sessoes secao 4: nunca o dono define valor, so se oferece)."""
    existing_kinds = {
        plan.kind for plan in db.query(Plan).filter(Plan.establishment_id == establishment_id).all()
    }
    for kind in PlanKind:
        if kind in existing_kinds:
            continue
        db.add(
            Plan(establishment_id=establishment_id, kind=kind, enabled=(kind == PlanKind.avulso))
        )
    db.commit()
