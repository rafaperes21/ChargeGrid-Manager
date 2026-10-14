"""Servico de polling - pergunta ao `SemsClient` (real ou simulado) as leituras atuais e
persiste em `charger_readings` (skill `integracao-sems-simulador`, secao 3).

`PollingService.poll_once` e a unidade testavel sem async/sleep; `run_forever` e so um loop
fino em volta dela para rodar como task de fundo (`python -m app.integracoes.polling`, ou
junto do FastAPI se `POLLING_ENABLED=true` - ver `app/main.py`).

Tolerancia a falha: se o `SemsClient` falhar (SEMS+ real fora do ar, por exemplo), a API
continua no ar - so contamos falhas consecutivas e, depois de N, marcamos os carregadores
como offline ate a fonte voltar. Chargers com sessao pending/active nao tem o status
sobrescrito por uma leitura ociosa - esse status e do motor de sessao (`services/sessions.py`),
o polling so grava a leitura crua e sincroniza o status de quem esta livre pra ele mexer.

Sprint 4 - cada tick tambem faz o papel de EMS (gestao de energia) do estabelecimento:
1. le inversor solar + bateria (`fetch_site_energy`);
2. controle de demanda: reparte o disponivel (rede ate `power_limit_kw` + solar + descarga
   possivel da bateria) entre os carregadores com sessao aberta (`services/demand_control`)
   e manda os tetos ao equipamento ANTES de ler os carregadores;
3. le os carregadores (ja respeitando o teto) e grava `charger_readings`;
4. despacho: decide solar -> bateria -> rede para a carga medida (`services/energy_dispatch`),
   grava `site_energy_readings` e manda o setpoint da bateria.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.integracoes.sems_client import SemsClient, get_sems_client
from app.models.charger import Charger, ChargerReading
from app.models.energy import SiteEnergyReading
from app.models.enums import ChargerStatus, ChargingSessionStatus
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.schemas.charger_reading import ChargerReadingContract, SiteEnergyContract
from app.services.demand_control import allocate_power
from app.services.energy_assets import battery_spec, get_site_assets
from app.services.energy_dispatch import BatterySpec, dispatch, max_discharge_kw

logger = logging.getLogger(__name__)


def _as_utc(value: datetime) -> datetime:
    """SQLite (testes) devolve naive em `DateTime(timezone=True)`; Postgres (prod) preserva.
    Normaliza pra UTC nos dois casos, senao a checagem de idempotencia abaixo compara um
    datetime aware (o que acabou de chegar) contra um naive (o que voltou do banco) e nunca
    bate - mesmo bug ja visto em `services/sessions.py`/`services/queue.py`."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


@dataclass
class _SitePlan:
    """O que o tick precisa lembrar de um estabelecimento entre o controle de demanda (antes
    de ler os carregadores) e o despacho (depois)."""

    establishment: Establishment
    site: SiteEnergyContract | None
    battery_serial: str | None
    battery: BatterySpec | None
    demand_limited_kw: Decimal


class PollingService:
    def __init__(self, sems_client: SemsClient, offline_after_failures: int | None = None) -> None:
        self.sems_client = sems_client
        self.offline_after_failures = (
            offline_after_failures
            if offline_after_failures is not None
            else settings.polling_offline_after_failures
        )
        self.consecutive_failures = 0

    def _busy_charger_ids(self, db: Session, charger_ids: list) -> set:
        rows = (
            db.query(ChargingSession.charger_id)
            .filter(
                ChargingSession.charger_id.in_(charger_ids),
                ChargingSession.status.in_(
                    [ChargingSessionStatus.pending, ChargingSessionStatus.active]
                ),
            )
            .all()
        )
        return {row[0] for row in rows}

    def _persist_idempotent(self, db: Session, rows: list[dict]) -> int:
        """Check-then-insert por (charger_id, timestamp): volume por tick e baixo (1 leitura
        por carregador), entao uma consulta previa e mais simples e mais portavel entre
        Postgres (prod) e SQLite (testes) do que upsert especifico de dialeto."""
        if not rows:
            return 0

        charger_ids = {row["charger_id"] for row in rows}
        timestamps = {row["timestamp"] for row in rows}
        existing = {
            (charger_id, _as_utc(timestamp))
            for charger_id, timestamp in db.query(
                ChargerReading.charger_id, ChargerReading.timestamp
            ).filter(
                ChargerReading.charger_id.in_(charger_ids),
                ChargerReading.timestamp.in_(timestamps),
            )
        }

        new_rows = [
            row
            for row in rows
            if (row["charger_id"], _as_utc(row["timestamp"])) not in existing
        ]
        if new_rows:
            db.bulk_insert_mappings(ChargerReading, new_rows)
        return len(new_rows)

    def _dt_hours(self) -> Decimal:
        return Decimal(settings.poll_interval_seconds) / Decimal(3600)

    async def _plan_sites(
        self, db: Session, chargers: list[Charger], busy_ids: set
    ) -> tuple[list[_SitePlan], dict[str, Decimal]]:
        chargers_by_est: dict[uuid.UUID, list[Charger]] = {}
        for charger in chargers:
            chargers_by_est.setdefault(charger.establishment_id, []).append(charger)

        plans: list[_SitePlan] = []
        caps: dict[str, Decimal] = {}
        for establishment in db.query(Establishment).filter(
            Establishment.id.in_(chargers_by_est.keys())
        ):
            inverter, battery_asset = get_site_assets(db, establishment.id)
            site = await self.sems_client.fetch_site_energy(
                inverter.sems_serial if inverter else None,
                battery_asset.sems_serial if battery_asset else None,
                db,
            )
            spec = battery_spec(battery_asset)
            solar_kw = site.solar_kw if site else Decimal("0")
            soc = site.battery_soc_pct if site else None
            available = establishment.power_limit_kw + solar_kw
            if spec is not None and soc is not None:
                available += max_discharge_kw(spec, soc, self._dt_hours())

            requested = {
                charger.sems_serial: charger.nominal_power_kw
                for charger in chargers_by_est[establishment.id]
                if charger.id in busy_ids
            }
            allocated = allocate_power(requested, available)
            caps.update(allocated)
            plans.append(
                _SitePlan(
                    establishment=establishment,
                    site=site,
                    battery_serial=battery_asset.sems_serial if battery_asset else None,
                    battery=spec,
                    demand_limited_kw=sum(requested.values(), Decimal("0"))
                    - sum(allocated.values(), Decimal("0")),
                )
            )
        return plans, caps

    def _persist_site_reading(
        self, db: Session, plan: _SitePlan, readings: list[ChargerReadingContract],
        serial_to_charger: dict[str, Charger],
    ) -> Decimal | None:
        """Grava a fotografia do fluxo e devolve o setpoint da bateria (ou None)."""
        own = [
            r for r in readings
            if (c := serial_to_charger.get(r.charger_serial)) is not None
            and c.establishment_id == plan.establishment.id
        ]
        if not own:
            return None
        # timestamp do device (o mais recente dos carregadores): mesma leitura repetida gera
        # o mesmo timestamp -> idempotente, igual a charger_readings.
        timestamp = max(r.timestamp for r in own)
        exists = (
            db.query(SiteEnergyReading.id)
            .filter(
                SiteEnergyReading.establishment_id == plan.establishment.id,
                SiteEnergyReading.timestamp == timestamp,
            )
            .first()
        )
        if exists is not None:
            return None

        result = dispatch(
            load_kw=sum((r.power_kw for r in own), Decimal("0")),
            solar_kw=plan.site.solar_kw if plan.site else Decimal("0"),
            battery=plan.battery,
            soc_pct=plan.site.battery_soc_pct if plan.site else None,
            grid_limit_kw=plan.establishment.power_limit_kw,
            dt_h=self._dt_hours(),
        )
        db.add(
            SiteEnergyReading(
                establishment_id=plan.establishment.id,
                timestamp=timestamp,
                load_kw=result.load_kw,
                solar_kw=result.solar_kw,
                solar_to_load_kw=result.solar_to_load_kw,
                battery_to_load_kw=result.battery_to_load_kw,
                grid_to_load_kw=result.grid_to_load_kw,
                solar_to_battery_kw=result.solar_to_battery_kw,
                solar_surplus_kw=result.solar_surplus_kw,
                battery_kw=result.battery_kw,
                battery_soc_pct=result.soc_before_pct,
                grid_limit_kw=plan.establishment.power_limit_kw,
                demand_limited_kw=plan.demand_limited_kw,
            )
        )
        return result.battery_kw if plan.battery is not None else None

    async def poll_once(self, db: Session) -> None:
        chargers = db.query(Charger).all()
        if not chargers:
            return

        serial_to_charger = {charger.sems_serial: charger for charger in chargers}
        busy_ids = self._busy_charger_ids(db, [charger.id for charger in chargers])

        try:
            plans, caps = await self._plan_sites(db, chargers, busy_ids)
            await self.sems_client.apply_setpoints(charger_caps_kw=caps)
            readings: list[ChargerReadingContract] = await self.sems_client.fetch_readings(
                list(serial_to_charger.keys()), db
            )
        except Exception:
            self.consecutive_failures += 1
            logger.warning(
                "Falha ao consultar SEMS+ (%s consecutiva(s))", self.consecutive_failures
            )
            if self.consecutive_failures >= self.offline_after_failures:
                for charger in chargers:
                    charger.status = ChargerStatus.offline
                db.commit()
            return

        self.consecutive_failures = 0

        rows = []
        for reading in readings:
            charger = serial_to_charger.get(reading.charger_serial)
            if charger is None:
                continue
            rows.append(
                {
                    "charger_id": charger.id,
                    "timestamp": reading.timestamp,
                    "power_kw": reading.power_kw,
                    "status": reading.status,
                    "total_energy_kwh": reading.total_energy_kwh,
                    "error_code": reading.error_code,
                }
            )
            if charger.id not in busy_ids:
                charger.status = reading.status

        self._persist_idempotent(db, rows)

        battery_setpoints: dict[str, Decimal] = {}
        for plan in plans:
            setpoint = self._persist_site_reading(db, plan, readings, serial_to_charger)
            if setpoint is not None and plan.battery_serial is not None:
                battery_setpoints[plan.battery_serial] = setpoint
        db.commit()

        if battery_setpoints:
            await self.sems_client.apply_setpoints(battery_setpoints_kw=battery_setpoints)

    async def run_forever(self, interval_seconds: int | None = None) -> None:
        interval = (
            interval_seconds if interval_seconds is not None else settings.poll_interval_seconds
        )
        while True:
            db = SessionLocal()
            try:
                await self.poll_once(db)
            except Exception:
                logger.exception("Erro inesperado no ciclo de polling")
            finally:
                db.close()
            await asyncio.sleep(interval)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    service = PollingService(get_sems_client())
    logger.info(
        "Polling iniciado (SEMS_SOURCE=%s, intervalo=%ss)",
        settings.sems_source,
        settings.poll_interval_seconds,
    )
    await service.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
