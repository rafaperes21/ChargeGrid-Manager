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
"""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.integracoes.sems_client import SemsClient, get_sems_client
from app.models.charger import Charger, ChargerReading
from app.models.enums import ChargerStatus, ChargingSessionStatus
from app.models.session import ChargingSession
from app.schemas.charger_reading import ChargerReadingContract

logger = logging.getLogger(__name__)


def _as_utc(value: datetime) -> datetime:
    """SQLite (testes) devolve naive em `DateTime(timezone=True)`; Postgres (prod) preserva.
    Normaliza pra UTC nos dois casos, senao a checagem de idempotencia abaixo compara um
    datetime aware (o que acabou de chegar) contra um naive (o que voltou do banco) e nunca
    bate - mesmo bug ja visto em `services/sessions.py`/`services/queue.py`."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


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

    async def poll_once(self, db: Session) -> None:
        chargers = db.query(Charger).all()
        if not chargers:
            return

        serial_to_charger = {charger.sems_serial: charger for charger in chargers}

        try:
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

        busy_ids = self._busy_charger_ids(db, [charger.id for charger in chargers])
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
        db.commit()

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
