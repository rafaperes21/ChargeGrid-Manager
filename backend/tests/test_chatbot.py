from decimal import Decimal

import requests

from app.core.config import Settings
from app.models.charger import Charger
from app.models.enums import ChargerModel, ChargerStatus, UserRole
from app.models.establishment import Establishment
from app.models.user import User
from app.services.chatbot import _describe_chargers, _describe_demand_forecast


def _register_and_login(client, email: str, role: str) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "senha1234", "full_name": "Fulano", "role": role},
    )
    response = client.post("/auth/login", json={"email": email, "password": "senha1234"})
    return response.json()["access_token"]


def _create_establishment_with_chargers(db_session) -> Establishment:
    owner = User(
        email="dono-chat@teste.com", hashed_password="x", full_name="Dono", role=UserRole.owner
    )
    db_session.add(owner)
    db_session.flush()

    establishment = Establishment(
        owner_id=owner.id,
        name="Estacionamento Teste",
        kind="estacionamento",
        phase="trifasico",
        grid_connection_kw=Decimal("75.000"),
        power_limit_kw=Decimal("40.000"),
    )
    db_session.add(establishment)
    db_session.flush()

    db_session.add_all(
        [
            Charger(
                establishment_id=establishment.id,
                sems_serial="HCA-G2-CHAT-001",
                model=ChargerModel.gw11k,
                spot_label="Vaga 01",
                status=ChargerStatus.livre,
                nominal_power_kw=Decimal("11.000"),
            ),
            Charger(
                establishment_id=establishment.id,
                sems_serial="HCA-G2-CHAT-002",
                model=ChargerModel.gw11k,
                spot_label="Vaga 02",
                status=ChargerStatus.problema,
                nominal_power_kw=Decimal("11.000"),
            ),
        ]
    )
    db_session.commit()
    return establishment


def test_describe_chargers_reflects_real_data(db_session):
    establishment = _create_establishment_with_chargers(db_session)

    description = _describe_chargers(db_session, establishment)

    assert "Vaga 01" in description
    assert "livre" in description
    assert "Vaga 02" in description
    assert "problema" in description
    assert "HCA-G2-CHAT-002" in description


def test_describe_chargers_empty_establishment(db_session):
    owner = User(
        email="dono-vazio@teste.com", hashed_password="x", full_name="Dono", role=UserRole.owner
    )
    db_session.add(owner)
    db_session.flush()
    establishment = Establishment(
        owner_id=owner.id,
        name="Vazio",
        kind="estacionamento",
        phase="trifasico",
        grid_connection_kw=Decimal("75.000"),
        power_limit_kw=Decimal("40.000"),
    )
    db_session.add(establishment)
    db_session.commit()

    assert (
        _describe_chargers(db_session, establishment)
        == "Nenhum carregador cadastrado neste estabelecimento."
    )


def test_describe_demand_forecast_handles_ia_unavailable(db_session, monkeypatch):
    establishment = _create_establishment_with_chargers(db_session)
    settings = Settings(ia_service_url="http://localhost:1")

    def _raise(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr("app.services.chatbot.requests.get", _raise)

    description = _describe_demand_forecast(establishment, settings)

    assert "não consegui" in description.lower() or "nao consegui" in description.lower()


def test_describe_demand_forecast_formats_real_response(db_session, monkeypatch):
    establishment = _create_establishment_with_chargers(db_session)
    settings = Settings()

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "status": "ok",
                "model_version": "prophet-1.1.6-v1",
                "peak_labels": ["amanha das 18h as 20h: alta demanda esperada"],
                "fallback_used": False,
                "backtest": {"overall_mae": 4.67, "overall_mape": None, "by_period": {}},
            }

    monkeypatch.setattr("app.services.chatbot.requests.get", lambda *a, **k: _FakeResponse())

    description = _describe_demand_forecast(establishment, settings)

    assert "prophet-1.1.6-v1" in description
    assert "18h as 20h" in description
    assert "4.67" in description


def test_describe_demand_forecast_insufficient_data(db_session, monkeypatch):
    establishment = _create_establishment_with_chargers(db_session)
    settings = Settings()

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"status": "insufficient_data"}

    monkeypatch.setattr("app.services.chatbot.requests.get", lambda *a, **k: _FakeResponse())

    description = _describe_demand_forecast(establishment, settings)

    assert "não" in description.lower() or "nao" in description.lower()
    assert "4 semanas" in description


def test_customer_gets_403_on_chat_endpoint(client):
    customer_token = _register_and_login(client, "cliente-chat@teste.com", "customer")

    response = client.post(
        "/chatbot/message",
        json={"establishment_id": "00000000-0000-0000-0000-000000000000", "message": "oi"},
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    assert response.status_code == 403


def test_owner_gets_404_for_another_owners_establishment(client):
    owner_a_token = _register_and_login(client, "dono-a@teste.com", "owner")
    owner_b_token = _register_and_login(client, "dono-b@teste.com", "owner")

    establishment_payload = {
        "name": "Estacionamento A",
        "kind": "estacionamento",
        "phase": "trifasico",
        "grid_connection_kw": "75.000",
        "power_limit_kw": "40.000",
    }
    establishment_id = client.post(
        "/establishments",
        json=establishment_payload,
        headers={"Authorization": f"Bearer {owner_a_token}"},
    ).json()["id"]

    response = client.post(
        "/chatbot/message",
        json={"establishment_id": establishment_id, "message": "como estao os carregadores?"},
        headers={"Authorization": f"Bearer {owner_b_token}"},
    )

    assert response.status_code == 404


class _FakeResponseMessage:
    def __init__(self, content):
        self.content = content
        self.tool_calls = []


class _FakeModelWithTools:
    def invoke(self, messages):
        return _FakeResponseMessage("resposta de teste do assistente")


class _FakeChatOllama:
    def __init__(self, **kwargs):
        pass

    def bind_tools(self, tools):
        return _FakeModelWithTools()


def test_chat_endpoint_returns_llm_reply(client, monkeypatch):
    monkeypatch.setattr("app.services.chatbot.ChatOllama", _FakeChatOllama)

    owner_token = _register_and_login(client, "dono-chat2@teste.com", "owner")
    establishment_id = client.post(
        "/establishments",
        json={
            "name": "Estacionamento Chat",
            "kind": "estacionamento",
            "phase": "trifasico",
            "grid_connection_kw": "75.000",
            "power_limit_kw": "40.000",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["id"]

    response = client.post(
        "/chatbot/message",
        json={"establishment_id": establishment_id, "message": "como estao os carregadores?"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "resposta de teste do assistente"
    assert body["tools_used"] == []
