def _register_and_login(client, email: str, role: str) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "senha1234", "full_name": "Fulano", "role": role},
    )
    response = client.post("/auth/login", json={"email": email, "password": "senha1234"})
    return response.json()["access_token"]


def _establishment_payload() -> dict:
    return {
        "name": "Estacionamento Teste",
        "kind": "estacionamento",
        "phase": "trifasico",
        "grid_connection_kw": "75.000",
        "power_limit_kw": "40.000",
    }


def test_customer_gets_403_on_owner_route(client):
    customer_token = _register_and_login(client, "cliente@teste.com", "customer")

    response = client.post(
        "/establishments",
        json=_establishment_payload(),
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    assert response.status_code == 403


def test_owner_can_create_establishment(client):
    owner_token = _register_and_login(client, "dono@teste.com", "owner")

    response = client.post(
        "/establishments",
        json=_establishment_payload(),
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Estacionamento Teste"


def test_request_without_token_is_unauthorized(client):
    response = client.post("/establishments", json=_establishment_payload())

    assert response.status_code == 401
