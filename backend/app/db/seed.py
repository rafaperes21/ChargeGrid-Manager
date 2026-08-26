"""Popula um estabelecimento de demo com carregadores, usuarios e planos coerentes.

Uso: `cd backend && python -m app.db.seed` (com o venv ativado e o Postgres de pe)."""

from decimal import Decimal

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.charger import Charger
from app.models.enums import ChargerModel, ChargerStatus, PlanKind, UserRole
from app.models.establishment import Establishment
from app.models.tariff import Plan
from app.models.user import User


def run() -> None:
    db = SessionLocal()
    try:
        existing = db.query(Establishment).first()
        if existing is not None:
            print("Seed ja aplicado - abortando para nao duplicar dados.")
            print(f"Establishment id: {existing.id}")
            return

        owner = User(
            email="dono@chargegrid.demo",
            hashed_password=hash_password("demo1234"),
            full_name="Dono do Estacionamento Central",
            role=UserRole.owner,
        )
        db.add(owner)
        db.flush()

        establishment = Establishment(
            owner_id=owner.id,
            name="Estacionamento Central",
            kind="estacionamento",
            phase="trifasico",
            grid_connection_kw=Decimal("75.000"),
            power_limit_kw=Decimal("40.000"),
        )
        db.add(establishment)
        db.flush()

        chargers = [
            Charger(
                establishment_id=establishment.id,
                sems_serial=f"HCA-G2-DEMO-{i:03d}",
                model=ChargerModel.gw11k,
                spot_label=f"Vaga {i:02d}",
                status=ChargerStatus.livre,
                nominal_power_kw=Decimal("11.000"),
            )
            for i in range(1, 5)
        ]
        db.add_all(chargers)

        plans = [
            Plan(
                establishment_id=establishment.id,
                name="Avulso",
                kind=PlanKind.avulso,
                priority=0,
            ),
            Plan(
                establishment_id=establishment.id,
                name="Mensal",
                kind=PlanKind.mensal,
                price=Decimal("149.9000"),
                free_kwh_allowance=Decimal("50.000"),
                discount_pct=Decimal("10.00"),
                priority=1,
            ),
        ]
        db.add_all(plans)

        customer = User(
            email="cliente@chargegrid.demo",
            hashed_password=hash_password("demo1234"),
            full_name="Cliente Demo",
            role=UserRole.customer,
            vehicle_model="BYD Dolphin",
            rfid_virtual_id="RFID-DEMO-0001",
        )
        db.add(customer)

        db.commit()
        print("Seed aplicado: 1 estabelecimento, 4 carregadores, 2 planos, 1 owner, 1 customer.")
        print(f"Establishment id: {establishment.id}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
