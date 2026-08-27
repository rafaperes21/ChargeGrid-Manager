import uuid

from app.core.config import Settings
from app.services.pricing_suggestions_proxy import fetch_pricing_suggestions


def _register_and_login(client, email: str, role: str) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "senha1234", "full_name": "Fulano", "role": role},
    )
    response = client.post("/auth/login", json={"email": email, "password": "senha1234"})
    return response.json()["access_token"]


def test_fetch_pricing_suggestions_survives_ia_being_down(monkeypatch):
    def _raise(*args, **kwargs):
        import requests

        raise requests.ConnectionError("ia indisponivel neste teste")

    monkeypatch.setattr("app.services.pricing_suggestions_proxy.requests.get", _raise)

    establishment_id = uuid.uuid4()
    result = fetch_pricing_suggestions(establishment_id, 48, Settings())

    assert result.status == "ia_unavailable"
    assert result.suggestions == []


def test_pricing_suggestions_endpoint_requires_owner(client):
    customer_token = _register_and_login(client, "cliente-precif@teste.com", "customer")
    response = client.get(
        "/pricing-suggestions/establishments/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 403


def test_pricing_suggestions_endpoint_requires_ownership_of_establishment(client, monkeypatch):
    owner_token = _register_and_login(client, "dono-precif@teste.com", "owner")
    establishment_id = client.post(
        "/establishments",
        json={
            "name": "Estacionamento Precificacao",
            "kind": "estacionamento",
            "phase": "trifasico",
            "grid_connection_kw": "75.000",
            "power_limit_kw": "40.000",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["id"]

    other_owner_token = _register_and_login(client, "outro-dono-precif@teste.com", "owner")
    response = client.get(
        f"/pricing-suggestions/establishments/{establishment_id}",
        headers={"Authorization": f"Bearer {other_owner_token}"},
    )
    assert response.status_code == 404
