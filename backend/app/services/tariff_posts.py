"""Postos tarifarios horarios da distribuidora (Tarifa Branca / horaria) - Sprint 4.

Valem para a Enel SP, distribuidora do Estacionamento Central da demo: ponta 17h30-20h30;
intermediario 16h30-17h30 e 20h30-21h30; fora de ponta no restante.
Fonte (consultada em 14/10/2026): https://www.enel.com.br/pt-saopaulo/tarifa-branca.html

Usado pelo modo de bateria "reserva para a ponta" (`energy_dispatch`) e pelo script de
cenarios. Simplificacao conhecida: a regra de fins de semana/feriados nao foi conferida em
fonte, entao aqui todo dia segue a mesma grade - o script de cenarios so aceita dia util.
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
PEAK = (time(17, 30), time(20, 30))
INTERMEDIATE = ((time(16, 30), time(17, 30)), (time(20, 30), time(21, 30)))


def tariff_post(at: datetime) -> str:
    """`ponta`, `intermediario` ou `fora_ponta` no instante `at` (aware, qualquer fuso)."""
    local = at.astimezone(LOCAL_TZ).time()
    if PEAK[0] <= local < PEAK[1]:
        return "ponta"
    if any(start <= local < end for start, end in INTERMEDIATE):
        return "intermediario"
    return "fora_ponta"
