from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ChargerStatus


class ChargerReadingContract(BaseModel):
    """Contrato de dados de qualquer fonte de leitura (SEMS+ real ou simulado) - skill
    `integracao-sems-simulador`, secao 2. `timestamp` e a chave de idempotencia: hora DA
    LEITURA no device, nao do momento em que o polling processou.

    `status` reaproveita o `ChargerStatus` do resto do app em vez de um enum paralelo -
    na pratica so `livre`/`carregando`/`problema`/`offline` sao valores que um device
    reportaria; `reservado` e estado de negocio nosso, nunca vem de uma leitura.
    """

    charger_serial: str
    timestamp: datetime
    power_kw: Decimal
    status: ChargerStatus
    total_energy_kwh: Decimal
    error_code: str | None = None
