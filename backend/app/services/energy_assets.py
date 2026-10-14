"""Leitura dos equipamentos de geracao/armazenamento de um estabelecimento (Sprint 4).
Ponto unico para transformar `EnergyAsset` (banco) em `BatterySpec` (despacho), usado pelo
polling, pelo simulador, pelo backfill historico e pelos endpoints de fluxo."""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.energy import EnergyAsset
from app.models.enums import BatteryDispatchMode, EnergyAssetKind
from app.services.energy_dispatch import BatterySpec
from app.services.tariff_posts import tariff_post


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


def battery_free_discharge(asset: EnergyAsset | None, at: datetime) -> bool:
    """Se a bateria pode descarregar livremente agora: sempre no autoconsumo; no modo reserva,
    so na ponta da distribuidora (fora dela, so para segurar o limite contratado)."""
    if asset is None or asset.dispatch_mode != BatteryDispatchMode.peak_reserve:
        return True
    return tariff_post(at) == "ponta"


def set_battery_mode(
    db: Session, establishment_id: uuid.UUID, mode: BatteryDispatchMode
) -> EnergyAsset | None:
    """Troca a politica de descarga da bateria do estabelecimento. `None` se nao houver
    bateria cadastrada. Vale a partir do proximo tick do polling."""
    _, battery = get_site_assets(db, establishment_id)
    if battery is None:
        return None
    battery.dispatch_mode = mode
    db.commit()
    db.refresh(battery)
    return battery
