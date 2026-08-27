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


def test_criar_estabelecimento_provisiona_os_tres_planos_do_catalogo(client):
    owner_token = _register_and_login(client, "dono-plano@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)

    response = client.get(
        f"/plans?establishment_id={establishment_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    plans = response.json()
    assert {p["kind"] for p in plans} == {"avulso", "mensal", "trimestral"}
    by_kind = {p["kind"]: p for p in plans}
    assert by_kind["avulso"]["enabled"] is True
    assert by_kind["mensal"]["enabled"] is False
    assert by_kind["mensal"]["discount_pct"] == "15.00"


def test_owner_alterna_enabled_de_um_plano(client):
    owner_token = _register_and_login(client, "dono-plano2@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    plans = client.get(
        f"/plans?establishment_id={establishment_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()
    mensal_id = next(p["id"] for p in plans if p["kind"] == "mensal")

    response = client.patch(
        f"/plans/{mensal_id}",
        json={"enabled": True},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is True

    reread = client.get(
        f"/plans?establishment_id={establishment_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()
    assert next(p for p in reread if p["kind"] == "mensal")["enabled"] is True


def test_owner_nao_pode_alterar_plano_de_outro_estabelecimento(client):
    owner_a_token = _register_and_login(client, "dono-plano-a@teste.com", "owner")
    establishment_a_id = _create_establishment(client, owner_a_token)
    plans_a = client.get(
        f"/plans?establishment_id={establishment_a_id}",
        headers={"Authorization": f"Bearer {owner_a_token}"},
    ).json()
    plan_a_id = plans_a[0]["id"]

    owner_b_token = _register_and_login(client, "dono-plano-b@teste.com", "owner")

    response = client.patch(
        f"/plans/{plan_a_id}",
        json={"enabled": True},
        headers={"Authorization": f"Bearer {owner_b_token}"},
    )
    assert response.status_code == 404


def test_patch_plano_inexistente_404(client):
    owner_token = _register_and_login(client, "dono-plano3@teste.com", "owner")

    response = client.patch(
        f"/plans/{uuid.uuid4()}",
        json={"enabled": True},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 404
