import uuid
from datetime import UTC, datetime, timedelta


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


def _create_charger(client, token, establishment_id) -> str:
    return client.post(
        "/chargers",
        json={
            "establishment_id": establishment_id,
            "sems_serial": f"SN-{uuid.uuid4().hex[:8]}",
            "model": "GW7K",
            "spot_label": "A1",
            "nominal_power_kw": "7.000",
        },
        headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]


def test_criar_e_listar_minhas_reservas(client):
    owner_token = _register_and_login(client, "dono-reserva@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    charger_id = _create_charger(client, owner_token, establishment_id)
    customer_token = _register_and_login(client, "cliente-reserva@teste.com", "customer")

    start = datetime.now(UTC) + timedelta(hours=2)
    created = client.post(
        "/reservations",
        json={
            "charger_id": charger_id,
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=1)).isoformat(),
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert created.status_code == 201
    assert created.json()["status"] == "pending"

    mine = client.get("/reservations/mine", headers={"Authorization": f"Bearer {customer_token}"})
    assert mine.status_code == 200
    assert len(mine.json()) == 1


def test_criar_reserva_falha_para_carregador_inexistente(client):
    customer_token = _register_and_login(client, "cliente-404@teste.com", "customer")
    start = datetime.now(UTC) + timedelta(hours=2)

    response = client.post(
        "/reservations",
        json={
            "charger_id": str(uuid.uuid4()),
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=1)).isoformat(),
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 404


def test_cancelar_reserva_de_outro_usuario_da_404(client):
    owner_token = _register_and_login(client, "dono-reserva2@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    charger_id = _create_charger(client, owner_token, establishment_id)
    customer_token = _register_and_login(client, "dono-da-reserva@teste.com", "customer")
    outro_token = _register_and_login(client, "outro-cliente@teste.com", "customer")

    start = datetime.now(UTC) + timedelta(hours=2)
    created = client.post(
        "/reservations",
        json={
            "charger_id": charger_id,
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=1)).isoformat(),
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    ).json()

    response = client.delete(
        f"/reservations/{created['id']}", headers={"Authorization": f"Bearer {outro_token}"}
    )
    assert response.status_code == 404


def test_cancelar_minha_reserva_com_sucesso(client):
    owner_token = _register_and_login(client, "dono-reserva3@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    charger_id = _create_charger(client, owner_token, establishment_id)
    customer_token = _register_and_login(client, "cancela-a-propria@teste.com", "customer")

    start = datetime.now(UTC) + timedelta(hours=2)
    created = client.post(
        "/reservations",
        json={
            "charger_id": charger_id,
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=1)).isoformat(),
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    ).json()

    response = client.delete(
        f"/reservations/{created['id']}", headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert response.status_code == 204


def test_agenda_do_estabelecimento_e_owner_only(client):
    owner_token = _register_and_login(client, "dono-reserva4@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    charger_id = _create_charger(client, owner_token, establishment_id)
    customer_token = _register_and_login(client, "cliente-agenda@teste.com", "customer")

    start = datetime.now(UTC) + timedelta(hours=2)
    client.post(
        "/reservations",
        json={
            "charger_id": charger_id,
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=1)).isoformat(),
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    owner_view = client.get(
        f"/establishments/{establishment_id}/reservations",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_view.status_code == 200
    assert owner_view.json()[0]["user_full_name"] == "Fulano"

    forbidden = client.get(
        f"/establishments/{establishment_id}/reservations",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert forbidden.status_code == 403


def test_chargers_status_e_publico_para_qualquer_usuario_autenticado(client):
    owner_token = _register_and_login(client, "dono-status@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    _create_charger(client, owner_token, establishment_id)
    customer_token = _register_and_login(client, "cliente-status@teste.com", "customer")

    response = client.get(
        f"/establishments/{establishment_id}/chargers-status",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "offline"


def test_chargers_status_404_para_estabelecimento_inexistente(client):
    customer_token = _register_and_login(client, "cliente-status-404@teste.com", "customer")
    response = client.get(
        f"/establishments/{uuid.uuid4()}/chargers-status",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 404
