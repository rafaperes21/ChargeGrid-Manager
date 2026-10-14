"""Cadastra o inversor solar e a bateria GoodWe (simulados) do Estacionamento Central -
Sprint 4. Idempotente: pode rodar quantas vezes quiser, e chamado tambem pelo `seed.py`.

Uso: `cd backend && python -m app.db.seed_energy`

Os numeros abaixo sao PREMISSAS DE SIMULACAO dimensionadas para 4 carregadores de 11 kW com
40 kW de limite contratado - nao sao especificacao de um modelo GoodWe especifico.
`TODO(datasheet)`: confirmar modelo/potencia/capacidade reais antes de qualquer orcamento.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.energy import EnergyAsset
from app.models.enums import EnergyAssetKind
from app.models.establishment import Establishment

DEMO_ESTABLISHMENT_NAME = "Estacionamento Central"
INVERTER_SERIAL = "GW-INV-DEMO-001"
BATTERY_SERIAL = "GW-BAT-DEMO-001"


def ensure_energy_assets(db: Session, establishment: Establishment) -> list[str]:
    """Cria o que faltar e devolve o que foi criado (vazio se ja existia tudo)."""
    created = []
    existing = {
        serial
        for (serial,) in db.query(EnergyAsset.sems_serial).filter(
            EnergyAsset.sems_serial.in_([INVERTER_SERIAL, BATTERY_SERIAL])
        )
    }
    if INVERTER_SERIAL not in existing:
        db.add(
            EnergyAsset(
                establishment_id=establishment.id,
                kind=EnergyAssetKind.inverter,
                sems_serial=INVERTER_SERIAL,
                model="Inversor híbrido GoodWe (simulado)",
                rated_kw=Decimal("20.000"),  # kWp do arranjo FV
            )
        )
        created.append(INVERTER_SERIAL)
    if BATTERY_SERIAL not in existing:
        db.add(
            EnergyAsset(
                establishment_id=establishment.id,
                kind=EnergyAssetKind.battery,
                sems_serial=BATTERY_SERIAL,
                model="Bateria GoodWe (simulada)",
                capacity_kwh=Decimal("20.000"),
                max_charge_kw=Decimal("10.000"),
                max_discharge_kw=Decimal("10.000"),
                min_soc_pct=Decimal("10.00"),
                round_trip_efficiency_pct=Decimal("90.00"),
            )
        )
        created.append(BATTERY_SERIAL)
    db.commit()
    return created


def run() -> None:
    db = SessionLocal()
    try:
        establishment = (
            db.query(Establishment).filter(Establishment.name == DEMO_ESTABLISHMENT_NAME).first()
        )
        if establishment is None:
            print("Estacionamento Central nao encontrado - rode `python -m app.db.seed` antes.")
            return
        created = ensure_energy_assets(db, establishment)
        print(f"Equipamentos de energia criados: {created or 'nenhum (ja existiam)'}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
