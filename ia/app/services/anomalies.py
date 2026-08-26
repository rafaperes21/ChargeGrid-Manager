"""Camada de regras deterministicas de deteccao de anomalias - ver skill
`ml-previsao-e-anomalias`, secao 3. Sempre ligada, roda antes/independente de qualquer
camada estatistica (fora do escopo desta PR). Cada regra devolve alertas com severidade e a(s)
leitura(s) que dispararam anexadas como evidencia - alerta sem evidencia e ignorado pelo
operador em uma semana.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.enums import ChargerStatus
from app.models import Charger, ChargerReading
from app.schemas.anomalies import AnomalyAlert, AnomalyEvidence


def fetch_recent_readings(
    db: Session, establishment_id: uuid.UUID, lookback_hours: int
) -> dict[uuid.UUID, list[ChargerReading]]:
    """Leituras dos ultimos `lookback_hours`, agrupadas por charger, ordenadas por timestamp."""
    since = datetime.now(tz=UTC) - timedelta(hours=lookback_hours)
    rows = db.execute(
        select(ChargerReading)
        .join(Charger, Charger.id == ChargerReading.charger_id)
        .where(Charger.establishment_id == establishment_id, ChargerReading.timestamp >= since)
        .order_by(ChargerReading.charger_id, ChargerReading.timestamp)
    ).scalars().all()

    by_charger: dict[uuid.UUID, list[ChargerReading]] = {}
    for reading in rows:
        by_charger.setdefault(reading.charger_id, []).append(reading)
    return by_charger


def _to_evidence(reading: ChargerReading) -> AnomalyEvidence:
    return AnomalyEvidence(
        timestamp=reading.timestamp,
        power_kw=reading.power_kw,
        status=reading.status.value,
        total_energy_kwh=reading.total_energy_kwh,
        error_code=reading.error_code,
    )


def _group_contiguous_runs(
    readings: list[ChargerReading], predicate: Callable[[ChargerReading], bool]
) -> list[list[ChargerReading]]:
    """Agrupa leituras consecutivas (na serie ja ordenada) que satisfazem `predicate` em
    blocos continuos - evita um alerta por leitura quando na verdade e um unico evento."""
    runs: list[list[ChargerReading]] = []
    current: list[ChargerReading] = []
    for reading in readings:
        if predicate(reading):
            current.append(reading)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def detect_zero_power_while_connected(
    charger: Charger, readings: list[ChargerReading], min_minutes: int
) -> list[AnomalyAlert]:
    """Potencia zero por mais de `min_minutes` com o device ainda reportando `carregando`."""
    runs = _group_contiguous_runs(
        readings, lambda r: r.power_kw == 0 and r.status == ChargerStatus.carregando
    )
    alerts = []
    for run in runs:
        duration = run[-1].timestamp - run[0].timestamp
        if duration < timedelta(minutes=min_minutes):
            continue
        minutes = int(duration.total_seconds() // 60)
        alerts.append(
            AnomalyAlert(
                charger_id=charger.id,
                charger_serial=charger.sems_serial,
                establishment_id=charger.establishment_id,
                rule="zero_power_connected",
                severity="high",
                message=(
                    f"Potencia zerada por {minutes} min com veiculo conectado - possivel "
                    "falha de equipamento."
                ),
                window_start=run[0].timestamp,
                window_end=run[-1].timestamp,
                evidence=[_to_evidence(r) for r in run],
            )
        )
    return alerts


def detect_over_nominal_power(
    charger: Charger, readings: list[ChargerReading], tolerance_pct: Decimal
) -> list[AnomalyAlert]:
    """Potencia acima da nominal do modelo (com tolerancia de medicao) - erro de medicao ou
    defeito."""
    limit = charger.nominal_power_kw * (Decimal("1") + tolerance_pct)
    runs = _group_contiguous_runs(readings, lambda r: r.power_kw > limit)
    alerts = []
    for run in runs:
        peak = max(r.power_kw for r in run)
        alerts.append(
            AnomalyAlert(
                charger_id=charger.id,
                charger_serial=charger.sems_serial,
                establishment_id=charger.establishment_id,
                rule="over_nominal_power",
                severity="high",
                message=(
                    f"Potencia de {peak} kW acima da nominal ({charger.nominal_power_kw} kW) - "
                    "erro de medicao ou defeito."
                ),
                window_start=run[0].timestamp,
                window_end=run[-1].timestamp,
                evidence=[_to_evidence(r) for r in run],
            )
        )
    return alerts


def detect_prolonged_offline(
    charger: Charger, readings: list[ChargerReading], cycles: int, cycle_minutes: int
) -> list[AnomalyAlert]:
    """Offline prolongado: status `offline` continuo, OU um gap de timestamp sem nenhuma
    leitura (poll silenciosamente falhando) - ambos acima de `cycles * cycle_minutes`."""
    threshold = timedelta(minutes=cycles * cycle_minutes)
    alerts = []

    offline_runs = _group_contiguous_runs(readings, lambda r: r.status == ChargerStatus.offline)
    for run in offline_runs:
        duration = run[-1].timestamp - run[0].timestamp
        if duration < threshold:
            continue
        alerts.append(_offline_alert(charger, run[0].timestamp, run[-1].timestamp, run))

    for previous, current in zip(readings, readings[1:]):
        gap = current.timestamp - previous.timestamp
        if gap >= threshold:
            alerts.append(
                _offline_alert(charger, previous.timestamp, current.timestamp, [previous, current])
            )

    return alerts


def _offline_alert(
    charger: Charger, window_start: datetime, window_end: datetime, evidence: list[ChargerReading]
) -> AnomalyAlert:
    minutes = int((window_end - window_start).total_seconds() // 60)
    return AnomalyAlert(
        charger_id=charger.id,
        charger_serial=charger.sems_serial,
        establishment_id=charger.establishment_id,
        rule="offline_prolonged",
        severity="medium",
        message=f"Carregador sem leituras validas por {minutes} min.",
        window_start=window_start,
        window_end=window_end,
        evidence=[_to_evidence(r) for r in evidence],
    )


def detect_energy_regression(
    charger: Charger, readings: list[ChargerReading]
) -> list[AnomalyAlert]:
    """Energia acumulada do device regredindo - reset ou corrupcao de dado."""
    alerts = []
    for previous, current in zip(readings, readings[1:]):
        if current.total_energy_kwh < previous.total_energy_kwh:
            alerts.append(
                AnomalyAlert(
                    charger_id=charger.id,
                    charger_serial=charger.sems_serial,
                    establishment_id=charger.establishment_id,
                    rule="energy_regression",
                    severity="medium",
                    message=(
                        f"Energia acumulada caiu de {previous.total_energy_kwh} kWh para "
                        f"{current.total_energy_kwh} kWh - possivel reset do acumulador."
                    ),
                    window_start=previous.timestamp,
                    window_end=current.timestamp,
                    evidence=[_to_evidence(previous), _to_evidence(current)],
                )
            )
    return alerts


def run_anomaly_rules(
    charger: Charger, readings: list[ChargerReading], settings: Settings
) -> list[AnomalyAlert]:
    """Roda as 4 regras deterministicas sobre a serie de leituras de um carregador."""
    if not readings:
        return []
    alerts: list[AnomalyAlert] = []
    alerts += detect_zero_power_while_connected(
        charger, readings, settings.anomaly_zero_power_minutes
    )
    alerts += detect_over_nominal_power(
        charger, readings, settings.anomaly_over_nominal_tolerance_pct
    )
    alerts += detect_prolonged_offline(
        charger, readings, settings.anomaly_offline_cycles, settings.anomaly_offline_cycle_minutes
    )
    alerts += detect_energy_regression(charger, readings)
    return sorted(alerts, key=lambda alert: alert.window_start)
