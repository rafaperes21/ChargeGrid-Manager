import uuid
from decimal import Decimal

from app.models.enums import PlanKind, UserRole
from app.models.establishment import Establishment
from app.models.tariff import Plan
from app.models.user import User
from app.services.plan_catalog import get_tier, plan_to_read, provision_plans_for_establishment


def _make_establishment(db) -> Establishment:
    owner = User(
        email=f"dono-{uuid.uuid4().hex[:6]}@teste.com", role=UserRole.owner, full_name="Dono"
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)

    establishment = Establishment(
        owner_id=owner.id,
        name="Estacionamento Teste",
        kind="estacionamento",
        phase="trifasico",
        grid_connection_kw=Decimal("75.000"),
        power_limit_kw=Decimal("40.000"),
    )
    db.add(establishment)
    db.commit()
    db.refresh(establishment)
    return establishment


def test_get_tier_traz_valores_fixos_por_kind():
    avulso = get_tier(PlanKind.avulso)
    mensal = get_tier(PlanKind.mensal)
    trimestral = get_tier(PlanKind.trimestral)

    assert avulso.discount_pct == Decimal("0.00")
    assert avulso.priority == 0
    assert mensal.discount_pct == Decimal("15.00")
    assert mensal.priority == 1
    assert trimestral.discount_pct == Decimal("25.00")
    assert trimestral.priority == 2
    # trimestral tem franquia maior que mensal (skill tarifacao-e-sessoes secao 4)
    assert trimestral.free_kwh_allowance > mensal.free_kwh_allowance


def test_provision_plans_for_establishment_cria_os_tres_niveis(db_session):
    establishment = _make_establishment(db_session)

    provision_plans_for_establishment(db_session, establishment.id)

    plans = db_session.query(Plan).filter(Plan.establishment_id == establishment.id).all()
    kinds = {plan.kind for plan in plans}
    assert kinds == {PlanKind.avulso, PlanKind.mensal, PlanKind.trimestral}

    by_kind = {plan.kind: plan for plan in plans}
    assert by_kind[PlanKind.avulso].enabled is True
    assert by_kind[PlanKind.mensal].enabled is False
    assert by_kind[PlanKind.trimestral].enabled is False


def test_provision_plans_for_establishment_e_idempotente_e_preserva_enabled(db_session):
    establishment = _make_establishment(db_session)
    provision_plans_for_establishment(db_session, establishment.id)

    mensal = (
        db_session.query(Plan)
        .filter(Plan.establishment_id == establishment.id, Plan.kind == PlanKind.mensal)
        .one()
    )
    mensal.enabled = True
    db_session.commit()

    provision_plans_for_establishment(db_session, establishment.id)

    plans = db_session.query(Plan).filter(Plan.establishment_id == establishment.id).all()
    assert len(plans) == 3  # nao duplica linhas ja existentes
    mensal_after = next(p for p in plans if p.kind == PlanKind.mensal)
    assert mensal_after.enabled is True  # nao reseta o toggle do proprietario


def test_plan_to_read_mescla_linha_do_banco_com_catalogo(db_session):
    establishment = _make_establishment(db_session)
    plan = Plan(establishment_id=establishment.id, kind=PlanKind.trimestral, enabled=True)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    read = plan_to_read(plan)

    assert read.id == plan.id
    assert read.enabled is True
    assert read.name == "Trimestral"
    assert read.discount_pct == Decimal("25.00")
    assert read.priority == 2
