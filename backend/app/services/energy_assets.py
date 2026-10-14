"""Leitura dos equipamentos de geracao/armazenamento de um estabelecimento (Sprint 4).
Ponto unico para transformar `EnergyAsset` (banco) em `BatterySpec` (despacho), usado pelo
polling, pelo simulador, pelo backfill historico e pelos endpoints de fluxo."""

import uuid

from sqlalchemy.orm import Session

from app.models.energy import EnergyAsset
from app.models.enums import EnergyAssetKind
from app.services.energy_dispatch import BatterySpec


def get_site_assets(
    db: Session, establishment_id: uuid.UUID
) -> tuple[EnergyAsset | None, EnergyAsset | None]:
    """(inversor, bateria) do estabelecimento - qualquer um pode nao existir."""
    assets = db.query(EnergyAsset).filter(EnergyAsset.establishment_id == establishment_id).all()
    inverter = next((a for a in assets if a.kind == EnergyAssetKind.inverter), None)
    battery = next((a for a in assets if a.kind == EnergyAssetKind.battery), None)
    return inverter, battery


def battery_spec(asset: EnergyAsset | None) -> BatterySpec | None:
    if asset is None or not asset.capacity_kwh:
        return None
    return BatterySpec(
        capacity_kwh=asset.capacity_kwh,
        max_charge_kw=asset.max_charge_kw,
        max_discharge_kw=asset.max_discharge_kw,
        min_soc_pct=asset.min_soc_pct,
        round_trip_efficiency_pct=asset.round_trip_efficiency_pct,
    )
