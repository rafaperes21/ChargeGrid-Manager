"""Fonte simulada de leituras - substitui o SEMS+ atras da interface `SemsClient` (skill
`integracao-sems-simulador`, secao 1 e 6).

Diferente do `simulador/historical_generator.py` (que gera dias inteiros de uma vez, pra
alimentar o treino da IA), este cliente gera leituras "ao vivo": a cada tick de polling,
olha se ha uma `ChargingSession` pending/active no carregador e devolve o ponto da curva
P(t) (`simulador/curve_engine.py`) correspondente ao tempo decorrido desde o inicio dela.

Por que correlacionar com sessao real em vez de sortear sessoes sozinho: quem controla
inicio/fim de sessao e o ChargeGrid-Manager, nao o hardware (CLAUDE.md). O carregador so
"carrega de verdade" quando o motor de sessao (`app/services/sessions.py`) abriu uma - o
simulador so precisa fazer a fisica bater com o que a sessao diz que esta acontecendo.
Carregador sem sessao aberta fica ocioso (potencia zero, `livre`).

Sprint 4 - solar, bateria e controle de demanda:
- `fetch_site_energy` faz o papel do inversor GoodWe (geracao FV, `simulador/solar.py`) e do
  BMS da bateria (SoC, `simulador/battery.py`).
- `apply_setpoints` recebe os comandos do backend: teto por carregador (o simulador respeita
  na proxima leitura - potencia = min(curva, teto)) e potencia da bateria (aplicada ao SoC
  pelo tempo que passar ate a proxima leitura). No HCA G2 real esse canal NAO existe via
  SEMS+ (Pull-only) - ver `RealSemsClient.apply_setpoints`.
- Simplificacao conhecida: com teto, a curva continua indexada pelo tempo decorrido (nao pela
  energia entregue) - o veiculo "termina" na mesma hora, so com menos kWh. Suficiente para a
  demo do fluxo de energia; nao use para estimar tempo de recarga sob limitacao.
"""

import random
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.integracoes.sems_client import SemsClient
from app.models.charger import Charger
from app.models.energy import EnergyAsset, SiteEnergyReading
from app.models.enums import ChargerStatus, ChargingSessionStatus
from app.models.session import ChargingSession
from app.schemas.charger_reading import ChargerReadingContract, SiteEnergyContract
from app.services.energy_assets import battery_spec
from app.services.energy_integration import trapezoidal_energy_kwh
from simulador.battery import SimulatedBattery
from simulador.curve_engine import CurveSample, generate_session_samples
from simulador.solar import SolarParams, solar_power_kw
from simulador.vehicles import pick_vehicle

_IDLE_ENERGY_QUANT = Decimal("0.000")


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class SimulatedSemsClient(SemsClient):
    def __init__(self) -> None:
        # cache por sessao: a curva (veiculo/SoC sorteados) tem que ser a mesma em todo
        # poll enquanto a sessao dura, senao a potencia pula de forma inconsistente entre
        # ticks. Chave = session.id, semente derivada dele -> mesma sessao sempre gera a
        # mesma curva, mesmo se o processo reiniciar e o cache for perdido.
        self._samples_by_session: dict[uuid.UUID, list[CurveSample]] = {}
        self._last_reading_by_charger: dict[uuid.UUID, tuple[datetime, Decimal]] = {}
        self._running_total_by_charger: dict[uuid.UUID, Decimal] = {}
        self._caps_by_serial: dict[str, Decimal] = {}
        self._batteries: dict[str, SimulatedBattery] = {}
        self._battery_last_ts: dict[str, datetime] = {}

    def _samples_for_session(
        self, session: ChargingSession, charger: Charger
    ) -> list[CurveSample]:
        cached = self._samples_by_session.get(session.id)
        if cached is not None:
            return cached

        rng = random.Random(session.id.int)
        vehicle = pick_vehicle(rng)
        initial_soc = Decimal(str(round(rng.uniform(0.15, 0.60), 3)))
        target_soc = Decimal(str(round(rng.uniform(0.80, 1.0), 3)))
        samples = generate_session_samples(
            charger.nominal_power_kw, vehicle, initial_soc, target_soc, rng
        )
        self._samples_by_session[session.id] = samples
        return samples

    def _sample_at(self, samples: list[CurveSample], elapsed) -> tuple[CurveSample, bool]:
        """Devolve a amostra vigente pro tempo decorrido, e se a curva ja terminou."""
        current = samples[0]
        for candidate in samples:
            if candidate.offset <= elapsed:
                current = candidate
            else:
                break
        return current, elapsed > samples[-1].offset

    def _accumulate_total_energy(
        self, charger_id: uuid.UUID, now: datetime, power_kw: Decimal
    ) -> Decimal:
        running_total = self._running_total_by_charger.get(charger_id, _IDLE_ENERGY_QUANT)
        last = self._last_reading_by_charger.get(charger_id)
        if last is not None:
            last_ts, last_power = last
            elapsed_hours = Decimal((now - last_ts).total_seconds()) / Decimal("3600")
            if elapsed_hours > 0:
                running_total += trapezoidal_energy_kwh(last_power, power_kw, elapsed_hours)
        self._running_total_by_charger[charger_id] = running_total
        self._last_reading_by_charger[charger_id] = (now, power_kw)
        return running_total

    async def fetch_readings(
        self, charger_serials: list[str], db: Session
    ) -> list[ChargerReadingContract]:
        chargers = (
            db.query(Charger).filter(Charger.sems_serial.in_(charger_serials)).all()
        )
        if not chargers:
            return []

        charger_ids = [charger.id for charger in chargers]
        open_session_by_charger = {
            session.charger_id: session
            for session in db.query(ChargingSession)
            .filter(
                ChargingSession.charger_id.in_(charger_ids),
                ChargingSession.status.in_(
                    [ChargingSessionStatus.pending, ChargingSessionStatus.active]
                ),
            )
            .all()
        }

        now = datetime.now(UTC)
        readings: list[ChargerReadingContract] = []

        for charger in chargers:
            session = open_session_by_charger.get(charger.id)
            if session is None:
                power_kw, status, error_code = Decimal("0.000"), ChargerStatus.livre, None
            else:
                samples = self._samples_for_session(session, charger)
                elapsed = now - _as_utc(session.started_at)
                sample, finished = self._sample_at(samples, elapsed)
                power_kw, status, error_code = sample.power_kw, sample.status, sample.error_code
                cap = self._caps_by_serial.get(charger.sems_serial)
                if cap is not None:
                    power_kw = min(power_kw, cap)
                if finished:
                    self._samples_by_session.pop(session.id, None)

            total_energy = self._accumulate_total_energy(charger.id, now, power_kw)
            readings.append(
                ChargerReadingContract(
                    charger_serial=charger.sems_serial,
                    timestamp=now,
                    power_kw=power_kw,
                    status=status,
                    total_energy_kwh=total_energy,
                    error_code=error_code,
                )
            )

        return readings

    async def apply_setpoints(
        self,
        charger_caps_kw: dict[str, Decimal] | None = None,
        battery_setpoints_kw: dict[str, Decimal] | None = None,
    ) -> None:
        if charger_caps_kw is not None:
            self._caps_by_serial = dict(charger_caps_kw)
        for serial, setpoint in (battery_setpoints_kw or {}).items():
            battery = self._batteries.get(serial)
            if battery is not None:
                battery.setpoint_kw = setpoint

    def _battery_for(self, asset: EnergyAsset, db: Session) -> SimulatedBattery | None:
        battery = self._batteries.get(asset.sems_serial)
        if battery is not None:
            return battery
        spec = battery_spec(asset)
        if spec is None:
            return None
        # Retoma do ultimo SoC persistido - reiniciar o processo nao pode "recarregar" a
        # bateria do nada (mesma preocupacao do odometro dos carregadores).
        last = (
            db.query(SiteEnergyReading.battery_soc_pct)
            .filter(
                SiteEnergyReading.establishment_id == asset.establishment_id,
                SiteEnergyReading.battery_soc_pct.isnot(None),
            )
            .order_by(SiteEnergyReading.timestamp.desc())
            .first()
        )
        soc = last[0] if last else Decimal(str(settings.sim_battery_initial_soc_pct))
        battery = SimulatedBattery(spec, soc)
        self._batteries[asset.sems_serial] = battery
        return battery

    async def fetch_site_energy(
        self, inverter_serial: str | None, battery_serial: str | None, db: Session
    ) -> SiteEnergyContract | None:
        if inverter_serial is None and battery_serial is None:
            return None
        now = datetime.now(UTC)
        serials = [s for s in (inverter_serial, battery_serial) if s is not None]
        assets = {
            asset.sems_serial: asset
            for asset in db.query(EnergyAsset).filter(EnergyAsset.sems_serial.in_(serials))
        }

        solar_kw = Decimal("0.000")
        inverter = assets.get(inverter_serial) if inverter_serial else None
        if inverter is not None and inverter.rated_kw:
            params = SolarParams(
                peak_kwp=inverter.rated_kw,
                sunrise_hour=settings.sim_solar_sunrise_hour,
                sunset_hour=settings.sim_solar_sunset_hour,
                performance_ratio=settings.sim_solar_performance_ratio,
                cloud_min=settings.sim_solar_cloud_min,
            )
            solar_kw = solar_power_kw(inverter.sems_serial, now, params)

        soc = None
        asset = assets.get(battery_serial) if battery_serial else None
        battery = self._battery_for(asset, db) if asset is not None else None
        if battery is not None:
            last_ts = self._battery_last_ts.get(asset.sems_serial)
            if last_ts is not None:
                elapsed_h = Decimal(str((now - last_ts).total_seconds() / 3600))
                battery.advance(elapsed_h)
            self._battery_last_ts[asset.sems_serial] = now
            soc = battery.soc_pct

        return SiteEnergyContract(timestamp=now, solar_kw=solar_kw, battery_soc_pct=soc)
