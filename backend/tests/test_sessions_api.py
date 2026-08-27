import uuid

from app.models.charger import Charger
from app.models.enums import ChargerStatus


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


def _create_charger(client, owner_token, establishment_id) -> str:
    return client.post(
        "/chargers",
        json={
            "establishment_id": establishment_id,
            "sems_serial": f"SN-{uuid.uuid4().hex[:8]}",
            "model": "GW7K",
            "spot_label": "A1",
            "nominal_power_kw": "7.000",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["id"]


def _set_charger_livre(db_session, charger_id: str) -> None:
    # nao existe endpoint pra isso - em producao quem atualiza e o polling (M2), aqui
    # simulamos o resultado dele direto no banco pra testar o router de sessoes isolado.
    charger = db_session.get(Charger, uuid.UUID(charger_id))
    charger.status = ChargerStatus.livre
    db_session.commit()


def _set_customer_rfid(client, token: str, rfid: str = "rfid-abc") -> None:
    client.patch(
        "/users/me",
        json={"rfid_virtual_id": rfid},
        headers={"Authorization": f"Bearer {token}"},
    )


def _setup_livre_charger(client, db_session) -> tuple[str, str]:
    """Devolve (owner_token, charger_id) de um carregador pronto pra receber sessao."""
    owner_token = _register_and_login(client, f"dono-{uuid.uuid4().hex[:8]}@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_token)
    charger_id = _create_charger(client, owner_token, establishment_id)
    _set_charger_livre(db_session, charger_id)
    return owner_token, charger_id


def test_start_session_via_api(client, db_session):
    _, charger_id = _setup_livre_charger(client, db_session)
    customer_token = _register_and_login(client, "cliente-sessao@teste.com", "customer")
    _set_customer_rfid(client, customer_token)

    response = client.post(
        "/sessions/start",
        json={"charger_id": charger_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["charger_id"] == charger_id


def test_start_session_falha_sem_rfid(client, db_session):
    _, charger_id = _setup_livre_charger(client, db_session)
    customer_token = _register_and_login(client, "cliente-sem-rfid@teste.com", "customer")

    response = client.post(
        "/sessions/start",
        json={"charger_id": charger_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 400


def test_start_session_falha_se_carregador_nao_existe(client):
    customer_token = _register_and_login(client, "cliente-404@teste.com", "customer")
    _set_customer_rfid(client, customer_token)

    response = client.post(
        "/sessions/start",
        json={"charger_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 404


def test_read_current_session_404_quando_nao_ha_sessao(client):
    customer_token = _register_and_login(client, "sem-sessao@teste.com", "customer")
    response = client.get(
        "/sessions/current", headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert response.status_code == 404


def test_read_current_session_retorna_sessao_pending(client, db_session):
    _, charger_id = _setup_livre_charger(client, db_session)
    customer_token = _register_and_login(client, "cliente-atual@teste.com", "customer")
    _set_customer_rfid(client, customer_token)
    client.post(
        "/sessions/start",
        json={"charger_id": charger_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    response = client.get(
        "/sessions/current", headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_receipt_404_para_quem_nao_e_dono_da_sessao_nem_do_estabelecimento(client, db_session):
    _, charger_id = _setup_livre_charger(client, db_session)
    customer_token = _register_and_login(client, "cliente-recibo@teste.com", "customer")
    _set_customer_rfid(client, customer_token)
    session_id = client.post(
        "/sessions/start",
        json={"charger_id": charger_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    ).json()["id"]

    outro_token = _register_and_login(client, "estranho-recibo@teste.com", "customer")
    response = client.get(
        f"/sessions/{session_id}/receipt", headers={"Authorization": f"Bearer {outro_token}"}
    )
    assert response.status_code == 404


def test_receipt_409_quando_sessao_ainda_nao_finalizada(client, db_session):
    _, charger_id = _setup_livre_charger(client, db_session)
    customer_token = _register_and_login(client, "cliente-recibo2@teste.com", "customer")
    _set_customer_rfid(client, customer_token)
    session_id = client.post(
        "/sessions/start",
        json={"charger_id": charger_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    ).json()["id"]

    response = client.get(
        f"/sessions/{session_id}/receipt", headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert response.status_code == 409


def test_list_sessions_e_owner_only(client, db_session):
    owner_token, _ = _setup_livre_charger(client, db_session)
    customer_token = _register_and_login(client, "cliente-lista@teste.com", "customer")

    forbidden = client.get(
        "/sessions?establishment_id=" + str(uuid.uuid4()),
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert forbidden.status_code == 403

    establishment_id = _create_establishment(client, owner_token)
    allowed = client.get(
        f"/sessions?establishment_id={establishment_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert allowed.status_code == 200
    assert allowed.json() == []
