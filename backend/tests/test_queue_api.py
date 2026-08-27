import uuid


def _register_and_login(client, email: str, role: str) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "senha1234", "full_name": "Fulano", "role": role},
    )
    response = client.post("/auth/login", json={"email": email, "password": "senha1234"})
    return response.json()["access_token"]


def _create_establishment(client, token) -> str:
    return client.post(
        "/establishments",
        json={
            "name": "Estacionamento Teste",
            "kind": "estacionamento",
            "phase": "trifasico",
            "grid_connection_kw": "75.000",
            "power_limit_kw": "40.000",
        },
        headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]


def test_join_e_ler_minha_posicao(client):
    owner_token = _register_and_login(client, "dono-fila@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    customer_token = _register_and_login(client, "cliente-fila@teste.com", "customer")

    joined = client.post(
        "/queue/join",
        json={"establishment_id": establishment_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert joined.status_code == 201

    mine = client.get("/queue/mine", headers={"Authorization": f"Bearer {customer_token}"})
    assert mine.status_code == 200
    body = mine.json()
    assert body["position"] == 1
    assert body["establishment_id"] == establishment_id


def test_join_falha_para_estabelecimento_inexistente(client):
    customer_token = _register_and_login(client, "cliente-fila-404@teste.com", "customer")
    response = client.post(
        "/queue/join",
        json={"establishment_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 404


def test_join_falha_se_ja_esta_em_uma_fila(client):
    owner_token = _register_and_login(client, "dono-fila2@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    customer_token = _register_and_login(client, "cliente-fila2@teste.com", "customer")
    client.post(
        "/queue/join",
        json={"establishment_id": establishment_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    response = client.post(
        "/queue/join",
        json={"establishment_id": establishment_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 409


def test_mine_404_quando_nao_esta_em_fila(client):
    customer_token = _register_and_login(client, "sem-fila@teste.com", "customer")
    response = client.get("/queue/mine", headers={"Authorization": f"Bearer {customer_token}"})
    assert response.status_code == 404


def test_leave_queue(client):
    owner_token = _register_and_login(client, "dono-fila3@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    customer_token = _register_and_login(client, "cliente-fila3@teste.com", "customer")
    client.post(
        "/queue/join",
        json={"establishment_id": establishment_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    left = client.delete("/queue/mine", headers={"Authorization": f"Bearer {customer_token}"})
    assert left.status_code == 204

    mine = client.get("/queue/mine", headers={"Authorization": f"Bearer {customer_token}"})
    assert mine.status_code == 404


def test_list_queue_e_owner_only(client):
    owner_token = _register_and_login(client, "dono-fila4@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    customer_token = _register_and_login(client, "cliente-fila4@teste.com", "customer")
    client.post(
        "/queue/join",
        json={"establishment_id": establishment_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    forbidden = client.get(
        f"/queue?establishment_id={establishment_id}",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert forbidden.status_code == 403

    allowed = client.get(
        f"/queue?establishment_id={establishment_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert allowed.status_code == 200
    assert len(allowed.json()) == 1
