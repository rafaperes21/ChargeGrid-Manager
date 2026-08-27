"""Interface unica para a fonte de leituras de potencia - skill `integracao-sems-simulador`,
secao 6. `SEMS_SOURCE` no `.env` escolhe a implementacao via `get_sems_client()`; nada fora
deste pacote deve saber se esta falando com o simulador ou com o SEMS+ real.

Critério de aceite a proteger: trocar `SEMS_SOURCE` nao pode exigir mudar nenhuma linha
fora de `app/integracoes/`.
"""

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.charger_reading import ChargerReadingContract


class SemsClient(ABC):
    @abstractmethod
    async def fetch_readings(
        self, charger_serials: list[str], db: Session
    ) -> list[ChargerReadingContract]:
        """Devolve a leitura mais recente de cada carregador pedido. `db` e usado apenas
        pela implementacao simulada (pra saber se ha sessao em andamento e gerar a curva
        certa) - o SEMS+ real ignoraria esse parametro, ele so existe pra manter as duas
        implementacoes com a mesma assinatura."""
        raise NotImplementedError


class RealSemsClient(SemsClient):
    """Stub - a API publica do HCA G2/SEMS+ nao existe ainda (contexto do desafio: modelo
    Pull, sem detalhes de autenticacao/rate limit/paginacao publicados). Quando existir,
    isolar essas preocupacoes aqui dentro; a interface `SemsClient` nao muda."""

    async def fetch_readings(
        self, charger_serials: list[str], db: Session
    ) -> list[ChargerReadingContract]:
        raise NotImplementedError(
            "SEMS+ real ainda nao esta disponivel - TODO quando a API existir "
            "(ver skill integracao-sems-simulador, secao 6)"
        )


_client: SemsClient | None = None


def get_sems_client() -> SemsClient:
    """Singleton: o cliente simulado guarda estado entre chamadas (curva de cada sessao em
    andamento) que precisa sobreviver de um tick de polling para o outro."""
    global _client
    if _client is not None:
        return _client

    if settings.sems_source == "simulator":
        from app.integracoes.simulated_sems_client import SimulatedSemsClient

        _client = SimulatedSemsClient()
    elif settings.sems_source == "real":
        _client = RealSemsClient()
    else:
        raise ValueError(f"SEMS_SOURCE desconhecido: {settings.sems_source!r}")

    return _client
