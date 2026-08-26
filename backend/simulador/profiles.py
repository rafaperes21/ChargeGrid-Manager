"""Perfis de dia tipico por tipo de estabelecimento, usados para sortear quando as sessoes
de carregamento comecam. Ver skill `integracao-sems-simulador`, secao 5.

Shopping tem pico noturno e de fim de semana; empresa tem pico as 8h e plato o dia todo, quase
zero fora do horario comercial; estacionamento tem uso diurno mais constante.
"""

import random
from dataclasses import dataclass
from datetime import date, time

_HOURS = range(24)


def _tiered_weights(
    peak_hours: set[int] | None = None,
    business_hours: set[int] | None = None,
    peak_weight: float = 1.0,
    business_weight: float = 1.0,
    off_weight: float = 0.1,
) -> tuple[float, ...]:
    peak_hours = peak_hours or set()
    business_hours = business_hours or set()
    weights = []
    for hour in _HOURS:
        if hour in peak_hours:
            weights.append(peak_weight)
        elif hour in business_hours:
            weights.append(business_weight)
        else:
            weights.append(off_weight)
    return tuple(weights)


@dataclass(frozen=True)
class EstablishmentProfile:
    kind: str
    sessions_per_charger_per_day: tuple[int, int]
    hourly_weights_weekday: tuple[float, ...]
    hourly_weights_weekend: tuple[float, ...]


PROFILE_BY_KIND: dict[str, EstablishmentProfile] = {
    "shopping": EstablishmentProfile(
        kind="shopping",
        sessions_per_charger_per_day=(1, 3),
        hourly_weights_weekday=_tiered_weights(
            peak_hours=set(range(18, 22)), business_hours=set(range(10, 18)),
            peak_weight=6.0, business_weight=1.5, off_weight=0.2,
        ),
        hourly_weights_weekend=_tiered_weights(
            peak_hours=set(range(14, 21)), business_hours=set(range(11, 14)),
            peak_weight=5.0, business_weight=2.0, off_weight=0.3,
        ),
    ),
    "estacionamento": EstablishmentProfile(
        kind="estacionamento",
        sessions_per_charger_per_day=(2, 4),
        hourly_weights_weekday=_tiered_weights(
            peak_hours=set(range(8, 11)) | set(range(17, 19)), business_hours=set(range(7, 20)),
            peak_weight=4.0, business_weight=2.5, off_weight=0.3,
        ),
        hourly_weights_weekend=_tiered_weights(
            business_hours=set(range(9, 18)), business_weight=1.8, off_weight=0.3,
        ),
    ),
    "empresa": EstablishmentProfile(
        kind="empresa",
        sessions_per_charger_per_day=(1, 2),
        hourly_weights_weekday=_tiered_weights(
            peak_hours={8, 9}, business_hours=set(range(9, 18)),
            peak_weight=8.0, business_weight=1.5, off_weight=0.02,
        ),
        hourly_weights_weekend=_tiered_weights(off_weight=0.02),
    ),
}


def sessions_for_day(profile: EstablishmentProfile, day: date, rng: random.Random) -> list[time]:
    """Sorteia horarios de inicio de sessao no dia, ponderados pelo perfil hora a hora."""
    is_weekend = day.weekday() >= 5
    weights = profile.hourly_weights_weekend if is_weekend else profile.hourly_weights_weekday
    min_sessions, max_sessions = profile.sessions_per_charger_per_day
    count = rng.randint(min_sessions, max_sessions)

    hours = rng.choices(list(_HOURS), weights=list(weights), k=count)
    start_times = [time(hour=hour, minute=rng.randint(0, 59)) for hour in hours]
    return sorted(start_times)
