from datetime import datetime, time
from decimal import Decimal

from app.models.enums import UserRole
from app.models.establishment import Establishment
from app.models.tariff import TariffRule
from app.models.user import User
from app.services.tariffs import resolve_active_tariff_rule


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


def _tariff_payload(
    establishment_id, days="0,1,2,3,4", start="18:00", end="21:00", price="1.5200", is_special=False
):
    return {
        "establishment_id": establishment_id,
        "name": "Pico",
        "days_of_week": days,
        "start_time_local": start,
        "end_time_local": end,
        "price_per_kwh": price,
        "is_special": is_special,
    }


def test_create_tariff_rule(client):
    token = _register_and_login(client, "dono-tar1@teste.com", "owner")
    establishment_id = _create_establishment(client, token)

    response = client.post(
        "/tariffs",
        json=_tariff_payload(establishment_id),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Pico"


def test_overlapping_rule_same_day_is_rejected(client):
    token = _register_and_login(client, "dono-tar2@teste.com", "owner")
    establishment_id = _create_establishment(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/tariffs",
        json=_tariff_payload(establishment_id, start="18:00", end="21:00"),
        headers=headers,
    )

    response = client.post(
        "/tariffs",
        json=_tariff_payload(establishment_id, start="19:00", end="22:00"),
        headers=headers,
    )

    assert response.status_code == 409


def test_non_overlapping_different_days_are_accepted(client):
    token = _register_and_login(client, "dono-tar3@teste.com", "owner")
    establishment_id = _create_establishment(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/tariffs",
        json=_tariff_payload(establishment_id, days="0,1,2,3,4", start="18:00", end="21:00"),
        headers=headers,
    )
    response = client.post(
        "/tariffs",
        json=_tariff_payload(establishment_id, days="5,6", start="18:00", end="21:00"),
        headers=headers,
    )

    assert response.status_code == 201


def test_ranges_crossing_midnight_conflict_correctly(client):
    """Skill tarifacao-e-sessoes: 23h-06h precisa conflitar com 05h-08h do dia seguinte -
    e o caso que o texto da skill chama atencao explicitamente."""
    token = _register_and_login(client, "dono-tar4@teste.com", "owner")
    establishment_id = _create_establishment(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    # segunda (0) 23h -> cruza meia-noite -> cobre ate terca (1) 06h
    client.post(
        "/tariffs",
        json=_tariff_payload(establishment_id, days="0", start="23:00", end="06:00"),
        headers=headers,
    )

    # terca (1) 05h-08h conflita com o trecho pos-meia-noite da regra acima (terca 00h-06h)
    response = client.post(
        "/tariffs",
        json=_tariff_payload(establishment_id, days="1", start="05:00", end="08:00"),
        headers=headers,
    )

    assert response.status_code == 409


def test_update_and_delete_require_ownership(client):
    owner_a_token = _register_and_login(client, "dono-tar5a@teste.com", "owner")
    owner_b_token = _register_and_login(client, "dono-tar5b@teste.com", "owner")
    establishment_id = _create_establishment(client, owner_a_token)

    rule_id = client.post(
        "/tariffs",
        json=_tariff_payload(establishment_id),
        headers={"Authorization": f"Bearer {owner_a_token}"},
    ).json()["id"]

    other_headers = {"Authorization": f"Bearer {owner_b_token}"}
    patch_response = client.patch(
        f"/tariffs/{rule_id}", json={"name": "Hack"}, headers=other_headers
    )
    assert patch_response.status_code == 404
    assert client.delete(f"/tariffs/{rule_id}", headers=other_headers).status_code == 404

    own_headers = {"Authorization": f"Bearer {owner_a_token}"}
    update_response = client.patch(
        f"/tariffs/{rule_id}", json={"name": "Pico ajustado"}, headers=own_headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Pico ajustado"

    assert client.delete(f"/tariffs/{rule_id}", headers=own_headers).status_code == 204


def test_special_rule_pode_sobrepor_regra_padrao(client):
    """"Aplicar" numa sugestao de precificacao (M8) cria uma tarifa especial pontual sem
    precisar fatiar a regra ampla existente - unica excecao a regra geral de nao sobrepor."""
    token = _register_and_login(client, "dono-tar6@teste.com", "owner")
    establishment_id = _create_establishment(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    regular = client.post(
        "/tariffs",
        json=_tariff_payload(establishment_id, days="0,1,2,3,4,5,6", start="00:00", end="23:59"),
        headers=headers,
    )
    assert regular.status_code == 201

    special = client.post(
        "/tariffs",
        json=_tariff_payload(
            establishment_id, days="4", start="18:00", end="19:00", price="2.4000", is_special=True
        ),
        headers=headers,
    )
    assert special.status_code == 201


def test_duas_regras_especiais_sobrepostas_ainda_e_rejeitado(client):
    token = _register_and_login(client, "dono-tar7@teste.com", "owner")
    establishment_id = _create_establishment(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/tariffs",
        json=_tariff_payload(
            establishment_id, days="4", start="18:00", end="19:00", price="2.4000", is_special=True
        ),
        headers=headers,
    )
    response = client.post(
        "/tariffs",
        json=_tariff_payload(
            establishment_id, days="4", start="18:30", end="19:30", price="2.6000", is_special=True
        ),
        headers=headers,
    )
    assert response.status_code == 409


def test_resolve_active_tariff_rule_prefere_especial_so_dentro_da_janela(db_session):
    owner = User(email="dono-resolve@teste.com", role=UserRole.owner, full_name="Fulano")
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    establishment = Establishment(
        owner_id=owner.id,
        name="Estacionamento Resolve",
        kind="estacionamento",
        phase="trifasico",
        grid_connection_kw=Decimal("75.000"),
        power_limit_kw=Decimal("40.000"),
    )
    db_session.add(establishment)
    db_session.commit()
    db_session.refresh(establishment)

    regular = TariffRule(
        establishment_id=establishment.id,
        name="Unica",
        days_of_week="0,1,2,3,4,5,6",
        start_time_local=time(0, 0),
        end_time_local=time(23, 59, 59),
        price_per_kwh=Decimal("2.0000"),
        is_special=False,
    )
    special = TariffRule(
        establishment_id=establishment.id,
        name="Sugestão IA — Sex 18h",
        days_of_week="4",  # sexta
        start_time_local=time(18, 0),
        end_time_local=time(19, 0),
        price_per_kwh=Decimal("2.4000"),
        is_special=True,
    )
    db_session.add_all([regular, special])
    db_session.commit()

    friday_inside_window = datetime(2026, 8, 28, 18, 30)  # 2026-08-28 e uma sexta-feira
    friday_outside_window = datetime(2026, 8, 28, 20, 0)
    saturday = datetime(2026, 8, 29, 18, 30)

    inside = resolve_active_tariff_rule(db_session, establishment.id, friday_inside_window)
    outside = resolve_active_tariff_rule(db_session, establishment.id, friday_outside_window)
    other_day = resolve_active_tariff_rule(db_session, establishment.id, saturday)

    assert inside.id == special.id
    assert outside.id == regular.id
    assert other_day.id == regular.id
