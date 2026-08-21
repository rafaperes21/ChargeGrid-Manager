def _owner_token(client, email: str = "dono2@teste.com") -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "senha1234", "full_name": "Dono", "role": "owner"},
    )
    response = client.post("/auth/login", json={"email": email, "password": "senha1234"})
    return response.json()["access_token"]


def test_create_and_list_establishment_happy_path(client):
    token = _owner_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/establishments",
        json={
            "name": "Shopping Teste",
            "kind": "shopping",
            "phase": "trifasico",
            "grid_connection_kw": "100.000",
            "power_limit_kw": "60.000",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    establishment_id = create_response.json()["id"]

    list_response = client.get("/establishments/me", headers=headers)
    assert list_response.status_code == 200
    assert any(item["id"] == establishment_id for item in list_response.json())


def test_create_charger_under_establishment(client):
    token = _owner_token(client, email="dono3@teste.com")
    headers = {"Authorization": f"Bearer {token}"}

    establishment_id = client.post(
        "/establishments",
        json={
            "name": "Estacionamento Teste 2",
            "kind": "estacionamento",
            "phase": "trifasico",
            "grid_connection_kw": "75.000",
            "power_limit_kw": "40.000",
        },
        headers=headers,
    ).json()["id"]

    charger_response = client.post(
        "/chargers",
        json={
            "establishment_id": establishment_id,
            "sems_serial": "HCA-G2-TEST-001",
            "model": "GW11K",
            "spot_label": "Vaga 01",
            "nominal_power_kw": "11.000",
        },
        headers=headers,
    )

    assert charger_response.status_code == 201
    assert charger_response.json()["status"] == "offline"
