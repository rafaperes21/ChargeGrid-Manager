import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

from app.models.charger import Charger, ChargerReading
from app.models.enums import ChargerStatus, ChargingSessionStatus
from app.models.session import ChargingSession
from app.models.tariff import TariffRule


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


def test_read_current_session_ativa_traz_valor_estimado(client, db_session):
    owner_token, charger_id = _setup_livre_charger(client, db_session)
    customer_token = _register_and_login(client, "cliente-estimado@teste.com", "customer")
    _set_customer_rfid(client, customer_token)

    establishment_id = client.get(
        "/establishments/me", headers={"Authorization": f"Bearer {owner_token}"}
    ).json()[0]["id"]
    db_session.add(
        TariffRule(
            establishment_id=uuid.UUID(establishment_id),
            name="Unica",
            days_of_week="0,1,2,3,4,5,6",
            start_time_local=time(0, 0),
            end_time_local=time(23, 59, 59),
            price_per_kwh=Decimal("2.0000"),
            is_special=False,
        )
    )
    db_session.commit()

    session_id = client.post(
        "/sessions/start",
        json={"charger_id": charger_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    ).json()["id"]
    session = db_session.get(ChargingSession, uuid.UUID(session_id))
    session.started_at = datetime.now(UTC) - timedelta(minutes=65)
    db_session.commit()

    # duas leituras de 6.000 kW, 60 min de intervalo -> 6.000 kWh exatos por trapezio,
    # nao aciona "encerrada por potencia zerada" (nenhuma leitura <= 0.050 kW).
    charger = db_session.get(Charger, uuid.UUID(charger_id))
    db_session.add_all(
        [
            ChargerReading(
                charger_id=charger.id,
                timestamp=session.started_at + timedelta(minutes=1),
                power_kw=Decimal("6.000"),
                status=ChargerStatus.carregando,
            ),
            ChargerReading(
                charger_id=charger.id,
                timestamp=session.started_at + timedelta(minutes=61),
                power_kw=Decimal("6.000"),
                status=ChargerStatus.carregando,
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/sessions/current", headers={"Authorization": f"Bearer {customer_token}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert Decimal(body["energy_kwh"]) == Decimal("6.000")
    assert Decimal(body["estimated_amount_due"]) == Decimal("12.0000")


def test_list_my_sessions_so_traz_terminais_e_e_ordenado(client, db_session):
    _, charger_id = _setup_livre_charger(client, db_session)
    customer_token = _register_and_login(client, "cliente-historico@teste.com", "customer")
    _set_customer_rfid(client, customer_token)

    session_id = client.post(
        "/sessions/start",
        json={"charger_id": charger_id},
        headers={"Authorization": f"Bearer {customer_token}"},
    ).json()["id"]

    mine_while_pending = client.get(
        "/sessions/mine", headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert mine_while_pending.json() == []

    session = db_session.get(ChargingSession, uuid.UUID(session_id))
    session.status = ChargingSessionStatus.error
    session.ended_at = datetime.now(UTC)
    db_session.commit()

    mine_after = client.get(
        "/sessions/mine", headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert len(mine_after.json()) == 1
    assert mine_after.json()[0]["id"] == session_id


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
