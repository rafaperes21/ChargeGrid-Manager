"""Agrega dado real (carregadores, ultima leitura, anomalias da IA) pro dashboard do
proprietario. Receita e sessoes ativas dependem do motor de tarifacao (M3), que nao existe -
sempre `None`, nunca um numero inventado.
"""

from decimal import ROUND_HALF_UP, Decimal

import requests
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.charger import Charger, ChargerReading
from app.models.establishment import Establishment
from app.schemas.dashboard import ChargerDashboardItem, DashboardAnomaly, DashboardResponse

UNAVAILABLE_REASON = "Motor de tarifacao (M3) ainda nao implementado."


def _latest_reading(db: Session, charger_id) -> ChargerReading | None:
    return (
        db.query(ChargerReading)
        .filter(ChargerReading.charger_id == charger_id)
        .order_by(ChargerReading.timestamp.desc())
        .first()
    )


def _fetch_anomalies(establishment_id, settings: Settings) -> tuple[list[DashboardAnomaly], bool]:
    url = f"{settings.ia_service_url}/anomalies/establishments/{establishment_id}"
    try:
        response = requests.get(url, params={"lookback_hours": 168}, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return [], True

    data = response.json()
    anomalies = [
        DashboardAnomaly(
            charger_serial=alert["charger_serial"],
            rule=alert["rule"],
            severity=alert["severity"],
            message=alert["message"],
        )
        for alert in data.get("alerts", [])
    ]
    return anomalies, False


def get_dashboard(
    db: Session, establishment: Establishment, settings: Settings
) -> DashboardResponse:
    chargers = (
        db.query(Charger)
        .filter(Charger.establishment_id == establishment.id)
        .order_by(Charger.spot_label)
        .all()
    )

    items = []
    total_power_kw = Decimal("0.000")
    for charger in chargers:
        reading = _latest_reading(db, charger.id)
        latest_power = reading.power_kw if reading else None
        if latest_power is not None:
            total_power_kw += latest_power
        items.append(
            ChargerDashboardItem(
                id=charger.id,
                spot_label=charger.spot_label,
                sems_serial=charger.sems_serial,
                model=charger.model,
                status=charger.status,
                nominal_power_kw=charger.nominal_power_kw,
                latest_power_kw=latest_power,
                latest_reading_at=reading.timestamp if reading else None,
            )
        )

    power_pct = None
    if establishment.power_limit_kw > 0:
        power_pct = (total_power_kw / establishment.power_limit_kw).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

    anomalies, ia_unavailable = _fetch_anomalies(establishment.id, settings)

    return DashboardResponse(
        establishment_id=establishment.id,
        establishment_name=establishment.name,
        chargers=items,
        total_power_kw=total_power_kw,
        power_limit_kw=establishment.power_limit_kw,
        power_pct=power_pct,
        anomalies=anomalies,
        ia_unavailable=ia_unavailable,
        revenue_today=None,
        active_sessions_count=None,
        unavailable_reason=UNAVAILABLE_REASON,
    )
