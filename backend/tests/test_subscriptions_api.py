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


def _enable_plan(client, owner_token, establishment_id, kind) -> str:
    plans = client.get(
        f"/plans?establishment_id={establishment_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()
    plan = next(p for p in plans if p["kind"] == kind)
    if not plan["enabled"]:
        client.patch(
            f"/plans/{plan['id']}",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
    return plan["id"]


def test_lista_de_planos_do_estabelecimento_so_traz_habilitados(client):
    owner_token = _register_and_login(client, "dono-sub1@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    customer_token = _register_and_login(client, "cliente-sub1@teste.com", "customer")

    response = client.get(
        f"/establishments/{establishment_id}/plans",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 200
    kinds = {p["kind"] for p in response.json()}
    assert kinds == {"avulso"}  # so avulso vem habilitado por padrao

    _enable_plan(client, owner_token, establishment_id, "mensal")

    response = client.get(
        f"/establishments/{establishment_id}/plans",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert {p["kind"] for p in response.json()} == {"avulso", "mensal"}


def test_cliente_assina_plano_mensal(client):
    owner_token = _register_and_login(client, "dono-sub2@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    mensal_id = _enable_plan(client, owner_token, establishment_id, "mensal")
    customer_token = _register_and_login(client, "cliente-sub2@teste.com", "customer")

    response = client.post(
        "/subscriptions",
        json={"plan_id": mensal_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["kind"] == "mensal"
    assert body["active"] is True

    current = client.get(
        f"/subscriptions/me?establishment_id={establishment_id}",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert current.status_code == 200
    assert current.json()["plan"]["kind"] == "mensal"


def test_trocar_de_plano_desativa_a_assinatura_anterior(client):
    owner_token = _register_and_login(client, "dono-sub3@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    mensal_id = _enable_plan(client, owner_token, establishment_id, "mensal")
    trimestral_id = _enable_plan(client, owner_token, establishment_id, "trimestral")
    customer_token = _register_and_login(client, "cliente-sub3@teste.com", "customer")

    client.post(
        "/subscriptions",
        json={"plan_id": mensal_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    response = client.post(
        "/subscriptions",
        json={"plan_id": trimestral_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 200
    assert response.json()["plan"]["kind"] == "trimestral"

    current = client.get(
        f"/subscriptions/me?establishment_id={establishment_id}",
        headers={"Authorization": f"Bearer {customer_token}"},
    ).json()
    assert current["plan"]["kind"] == "trimestral"


def test_assinar_avulso_desativa_assinatura_e_devolve_null(client):
    owner_token = _register_and_login(client, "dono-sub4@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    mensal_id = _enable_plan(client, owner_token, establishment_id, "mensal")
    avulso_id = _enable_plan(client, owner_token, establishment_id, "avulso")
    customer_token = _register_and_login(client, "cliente-sub4@teste.com", "customer")

    client.post(
        "/subscriptions",
        json={"plan_id": mensal_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    response = client.post(
        "/subscriptions",
        json={"plan_id": avulso_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 200
    assert response.json() is None

    current = client.get(
        f"/subscriptions/me?establishment_id={establishment_id}",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert current.json() is None


def test_assinar_plano_desabilitado_404(client):
    owner_token = _register_and_login(client, "dono-sub5@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    plans = client.get(
        f"/plans?establishment_id={establishment_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()
    trimestral_id = next(p["id"] for p in plans if p["kind"] == "trimestral")
    customer_token = _register_and_login(client, "cliente-sub5@teste.com", "customer")

    response = client.post(
        "/subscriptions",
        json={"plan_id": trimestral_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 404


def test_assinar_plano_inexistente_404(client):
    customer_token = _register_and_login(client, "cliente-sub6@teste.com", "customer")

    response = client.post(
        "/subscriptions",
        json={"plan_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 404
