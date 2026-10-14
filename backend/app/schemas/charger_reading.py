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


class SiteEnergyContract(BaseModel):
    """Leitura do lado de geracao/armazenamento da planta (Sprint 4): o que o inversor GoodWe
    reporta de geracao solar e o que a bateria reporta de SoC. Mesmo principio do contrato
    acima - qualquer fonte (SEMS+ real ou simulador) devolve isto, e o resto do sistema nao
    sabe qual delas esta falando. `None` = a planta nao tem aquele equipamento."""

    timestamp: datetime
    solar_kw: Decimal = Decimal("0.000")
    battery_soc_pct: Decimal | None = None
