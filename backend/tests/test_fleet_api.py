def _register_and_login(client, email: str, role: str) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "senha1234", "full_name": "Fulano", "role": role},
    )
    response = client.post("/auth/login", json={"email": email, "password": "senha1234"})
    return response.json()["access_token"]


def test_fleet_overview_e_owner_only(client):
    owner_token = _register_and_login(client, "dono-frota@teste.com", "owner")
    customer_token = _register_and_login(client, "cliente-frota@teste.com", "customer")

    owner_response = client.get(
        "/fleet/overview", headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert owner_response.status_code == 200
    assert "establishments_count" in owner_response.json()

    customer_response = client.get(
        "/fleet/overview", headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert customer_response.status_code == 403


def test_fleet_overview_requer_autenticacao(client):
    response = client.get("/fleet/overview")
    assert response.status_code == 401


def test_fleet_impact_e_publico(client):
    response = client.get("/fleet/impact")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "establishments_count",
        "total_kwh_managed",
        "total_revenue_processed",
        "co2_avoided_kg",
    }
