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
    assert create_response.json()["max_increase_pct"] == "20.00"
    assert create_response.json()["max_decrease_pct"] == "20.00"

    list_response = client.get("/establishments/me", headers=headers)
    assert list_response.status_code == 200
    assert any(item["id"] == establishment_id for item in list_response.json())


def test_update_establishment_pricing_limits(client):
    token = _owner_token(client, email="dono-limites@teste.com")
    headers = {"Authorization": f"Bearer {token}"}

    establishment_id = client.post(
        "/establishments",
        json={
            "name": "Estacionamento Limites",
            "kind": "estacionamento",
            "phase": "trifasico",
            "grid_connection_kw": "75.000",
            "power_limit_kw": "40.000",
        },
        headers=headers,
    ).json()["id"]

    response = client.patch(
        f"/establishments/{establishment_id}",
        json={"max_increase_pct": "10.00"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["max_increase_pct"] == "10.00"
    assert response.json()["max_decrease_pct"] == "20.00"


def test_update_establishment_requires_ownership(client):
    owner_token = _owner_token(client, email="dono-a@teste.com")
    other_owner_token = _owner_token(client, email="dono-b@teste.com")

    establishment_id = client.post(
        "/establishments",
        json={
            "name": "Estacionamento A",
            "kind": "estacionamento",
            "phase": "trifasico",
            "grid_connection_kw": "75.000",
            "power_limit_kw": "40.000",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["id"]

    response = client.patch(
        f"/establishments/{establishment_id}",
        json={"max_increase_pct": "5.00"},
        headers={"Authorization": f"Bearer {other_owner_token}"},
    )

    assert response.status_code == 404


def test_customer_can_list_all_establishments(client):
    owner_token = _owner_token(client, email="dono-list@teste.com")
    client.post(
        "/establishments",
        json={
            "name": "Shopping Lista",
            "kind": "shopping",
            "phase": "trifasico",
            "grid_connection_kw": "100.000",
            "power_limit_kw": "60.000",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    client.post(
        "/auth/register",
        json={
            "email": "cliente-list@teste.com",
            "password": "senha1234",
            "full_name": "Cliente",
            "role": "customer",
        },
    )
    customer_token = client.post(
        "/auth/login", json={"email": "cliente-list@teste.com", "password": "senha1234"}
    ).json()["access_token"]

    response = client.get(
        "/establishments", headers={"Authorization": f"Bearer {customer_token}"}
    )

    assert response.status_code == 200
    assert any(item["name"] == "Shopping Lista" for item in response.json())


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


def test_customer_can_list_chargers_for_the_map(client):
    owner_token = _owner_token(client, email="dono-mapa@teste.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    establishment_id = client.post(
        "/establishments",
        json={
            "name": "Estacionamento Mapa",
            "kind": "estacionamento",
            "phase": "trifasico",
            "grid_connection_kw": "75.000",
            "power_limit_kw": "40.000",
        },
        headers=owner_headers,
    ).json()["id"]
    client.post(
        "/chargers",
        json={
            "establishment_id": establishment_id,
            "sems_serial": "HCA-G2-MAPA-001",
            "model": "GW11K",
            "spot_label": "Vaga 01",
            "nominal_power_kw": "11.000",
        },
        headers=owner_headers,
    )

    client.post(
        "/auth/register",
        json={
            "email": "cliente-mapa@teste.com",
            "password": "senha1234",
            "full_name": "Cliente",
            "role": "customer",
        },
    )
    customer_token = client.post(
        "/auth/login", json={"email": "cliente-mapa@teste.com", "password": "senha1234"}
    ).json()["access_token"]

    response = client.get(
        f"/chargers?establishment_id={establishment_id}",
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
