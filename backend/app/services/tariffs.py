"""Validacao de faixas de tarifa - skill `tarifacao-e-sessoes` secao 2: as faixas de um
mesmo dia nao podem se sobrepor. Faixas que cruzam a meia-noite (ex.: 23h-06h) viram dois
intervalos - "e onde o bug aparece", segundo a propria skill.
"""

import uuid
from datetime import time

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
    exclude_id: uuid.UUID | None = None,
) -> None:
    query = db.query(TariffRule).filter(TariffRule.establishment_id == establishment_id)
    if exclude_id is not None:
        query = query.filter(TariffRule.id != exclude_id)
    existing_rules = query.all()

    new_intervals = _expand_to_day_intervals(days_of_week, start_time_local, end_time_local)

    for existing_rule in existing_rules:
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
