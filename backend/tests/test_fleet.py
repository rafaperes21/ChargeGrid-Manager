from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.config import Settings
from app.models.charger import Charger
from app.models.enums import ChargerModel, ChargerStatus, ChargingSessionStatus, UserRole
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.models.user import User
from app.services.fleet import get_fleet_impact, get_fleet_overview
from app.services.sustainability import co2_avoided_kg


def _raise_connection_error(*args, **kwargs):
    import requests

    raise requests.ConnectionError("ia indisponivel neste teste")


def _make_establishment_with_finished_session(
    db, *, name: str, energy_kwh: str, amount: str
) -> Establishment:
    owner = User(
        email=f"dono-{name}@teste.com", hashed_password="x", full_name="Dono", role=UserRole.owner
    )
    db.add(owner)
    db.flush()

    establishment = Establishment(
        owner_id=owner.id,
        name=name,
        kind="estacionamento",
        phase="trifasico",
        grid_connection_kw=Decimal("75.000"),
        power_limit_kw=Decimal("40.000"),
    )
    db.add(establishment)
    db.flush()

    charger = Charger(
        establishment_id=establishment.id,
        sems_serial=f"SN-{name}",
        model=ChargerModel.gw11k,
        spot_label="Vaga 01",
        status=ChargerStatus.livre,
        nominal_power_kw=Decimal("11.000"),
    )
    db.add(charger)
    db.flush()

    customer = User(
        email=f"cliente-{name}@teste.com",
        hashed_password="x",
        full_name="Cliente",
        role=UserRole.customer,
    )
    db.add(customer)
    db.flush()

    now = datetime.now(tz=UTC)
    session = ChargingSession(
        user_id=customer.id,
        charger_id=charger.id,
        establishment_id=establishment.id,
        status=ChargingSessionStatus.finished,
        started_at=now - timedelta(hours=1),
        ended_at=now,
        energy_kwh=Decimal(energy_kwh),
        amount_due=Decimal(amount),
    )
    db.add(session)
    db.commit()
    return establishment


def test_get_fleet_overview_soma_entre_todos_os_estabelecimentos(db_session, monkeypatch):
    monkeypatch.setattr("app.services.dashboard.requests.get", _raise_connection_error)
    _make_establishment_with_finished_session(
        db_session, name="a", energy_kwh="10.000", amount="20.0000"
    )
    _make_establishment_with_finished_session(
        db_session, name="b", energy_kwh="5.000", amount="8.0000"
    )

    result = get_fleet_overview(db_session, Settings())

    assert result.establishments_count == 2
    assert result.chargers_count == 2
    assert result.total_kwh_managed == Decimal("15.000")
    assert result.total_revenue_processed == Decimal("28.0000")
    assert result.finished_sessions_count == 2
    assert result.ia_unavailable is True
    assert result.anomalies_detected_count == 0


def test_get_fleet_overview_sem_estabelecimentos_e_honesto_com_zero(db_session):
    result = get_fleet_overview(db_session, Settings())

    assert result.establishments_count == 0
    assert result.total_kwh_managed == Decimal("0.000")
    assert result.total_revenue_processed == Decimal("0.0000")
    assert result.ia_unavailable is False


def test_get_fleet_impact_inclui_co2_evitado(db_session, monkeypatch):
    monkeypatch.setattr("app.services.dashboard.requests.get", _raise_connection_error)
    _make_establishment_with_finished_session(
        db_session, name="c", energy_kwh="16.000", amount="30.0000"
    )
    settings = Settings()

    result = get_fleet_impact(db_session, settings)

    assert result.total_kwh_managed == Decimal("16.000")
    assert result.co2_avoided_kg == co2_avoided_kg(Decimal("16.000"), settings)
    # nao expoe contagem de sessoes nem nada por-estabelecimento, so os 3 numeros de impacto
    assert not hasattr(result, "finished_sessions_count")


def test_co2_avoided_kg_usa_fatores_da_config():
    settings = Settings(avg_vehicle_kwh_per_km=0.2, co2_emission_factor_kg_per_km=0.1)

    result = co2_avoided_kg(Decimal("20.000"), settings)

    # 20 kWh / 0.2 kWh/km = 100 km; 100 km * 0.1 kg/km = 10 kg
    assert result == Decimal("10.0")
