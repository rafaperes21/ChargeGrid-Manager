"""Validacao de faixas de tarifa - skill `tarifacao-e-sessoes` secao 2: as faixas de um
mesmo dia nao podem se sobrepor. Faixas que cruzam a meia-noite (ex.: 23h-06h) viram dois
intervalos - "e onde o bug aparece", segundo a propria skill.

Excecao: uma faixa `is_special=True` PODE se sobrepor a uma faixa padrao (nao-especial) no
mesmo horario - e assim que "Aplicar" numa sugestao de precificacao (M8) cria uma tarifa
pontual pra um (dia, hora) especifico sem precisar fatiar a regra ampla existente em varios
pedacos. Especial-com-especial e padrao-com-padrao continuam bloqueados (senao duas regras
do mesmo tipo disputariam o mesmo horario sem criterio de desempate). Quando ha sobreposicao
valida, `resolve_active_tariff_rule` sempre prefere a especial - skill tarifacao-e-sessoes
nao definia isso porque o cenario (IA aplicando ajuste pontual sobre uma tarifa ampla) nao
existia ainda quando a secao 2 foi escrita.
"""

import uuid
from datetime import datetime, time

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.tariff import TariffRule

_END_OF_DAY = time(23, 59, 59, 999999)
_START_OF_DAY = time(0, 0)


def _expand_to_day_intervals(
    days_of_week: str, start: time, end: time
) -> list[tuple[int, time, time]]:
    """Devolve (dia_da_semana, inicio, fim) por dia coberto. Faixa que cruza a meia-noite
    (fim <= inicio) vira dois intervalos: ate o fim do dia, e do inicio do dia seguinte."""
    days = [int(d) for d in days_of_week.split(",") if d != ""]
    intervals: list[tuple[int, time, time]] = []
    for day in days:
        if end > start:
            intervals.append((day, start, end))
        else:
            intervals.append((day, start, _END_OF_DAY))
            intervals.append(((day + 1) % 7, _START_OF_DAY, end))
    return intervals


def validate_no_overlap(
    db: Session,
    establishment_id: uuid.UUID,
    days_of_week: str,
    start_time_local: time,
    end_time_local: time,
    is_special: bool = False,
    exclude_id: uuid.UUID | None = None,
) -> None:
    query = db.query(TariffRule).filter(TariffRule.establishment_id == establishment_id)
    if exclude_id is not None:
        query = query.filter(TariffRule.id != exclude_id)
    existing_rules = query.all()

    new_intervals = _expand_to_day_intervals(days_of_week, start_time_local, end_time_local)

    for existing_rule in existing_rules:
        # especial sobre padrao e a excecao permitida (ver docstring do modulo) - so
        # bloqueia quando as duas faixas sao do mesmo tipo.
        if is_special != existing_rule.is_special:
            continue
        existing_intervals = _expand_to_day_intervals(
            existing_rule.days_of_week, existing_rule.start_time_local, existing_rule.end_time_local
        )
        for new_day, new_start, new_end in new_intervals:
            for existing_day, existing_start, existing_end in existing_intervals:
                same_day = new_day == existing_day
                overlaps = new_start < existing_end and existing_start < new_end
                if same_day and overlaps:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Faixa se sobrepoe com '{existing_rule.name}' no mesmo dia.",
                    )


def resolve_active_tariff_rule(
    db: Session, establishment_id: uuid.UUID, local_dt: datetime
) -> TariffRule | None:
    """Acha a regra de tarifa vigente num instante em horario local do estabelecimento.

    A tarifa e congelada no inicio da sessao (skill tarifacao-e-sessoes secao 1): chamar
    uma unica vez com o `started_at` convertido pra local, nunca recalcular no fechamento -
    senao o extrato de uma sessao que atravessou a virada de faixa muda de valor.

    Quando uma faixa `is_special` se sobrepoe a uma padrao (unica sobreposicao permitida por
    `validate_no_overlap`), a especial sempre vence - e o mesmo criterio que faz "Aplicar"
    numa sugestao de precificacao (M8) valer sem precisar fatiar a regra ampla existente.
    """
    weekday = local_dt.weekday()  # 0=segunda, igual a convencao de `days_of_week`
    moment = local_dt.time()

    rules = db.query(TariffRule).filter(TariffRule.establishment_id == establishment_id).all()
    matched_regular: TariffRule | None = None
    for rule in rules:
        intervals = _expand_to_day_intervals(
            rule.days_of_week, rule.start_time_local, rule.end_time_local
        )
        for day, start, end in intervals:
            if day == weekday and start <= moment < end:
                if rule.is_special:
                    return rule
                matched_regular = rule
    return matched_regular
