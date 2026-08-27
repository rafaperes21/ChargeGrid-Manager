"""Historico de demonstracao pro Estacionamento Central - PROVISORIO.

Pedido do usuario em 27/08/2026 pra gravar a demo com dado variado (nao so o cliente unico
de `seed.py`). Os numeros de horario/duracao/energia por sessao sao inspirados no padrao
real de um registro de carregamento do HCA G2 da FIAP (NS 57000HPA247L0002, periodo
29/07-27/08/2026, 158.90 kWh em 18 sessoes - PDF anexado pelo usuario), resample com jitter
determinístico por cliente. **Nao sao sessoes de clientes reais** - sao dado de demonstracao
"real e possivel", ver `tasks/milestones/M11-impacto-goodwe.md`. Trocar por dado de producao
assim que houver clientes de verdade.

Uso: `cd backend && python -m app.db.seed_demo_history` depois do `seed.py` normal (precisa
do Estacionamento Central e dos 4 carregadores ja existirem). Idempotente por e-mail de
cliente - rodar de novo nao duplica quem ja foi criado.
"""

import random
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.charger import Charger, ChargerReading
from app.models.enums import ChargerStatus, ChargingSessionStatus, PlanKind, UserRole
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.models.tariff import Plan, TariffRule
from app.models.user import Subscription, User
from app.services.pricing import calculate_session_amount
from app.services.sessions import _resolve_plan_context
from app.services.tariffs import resolve_active_tariff_rule

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
HISTORY_DAYS = 30
READING_STEP_MINUTES = 10

# (hora local de inicio, duracao em minutos, energia em kWh) - direto do PDF real da FIAP,
# um carregador so (NS 57000HPA247L0002). Serve de "formato" pra gerar sessoes plausiveis
# pros clientes de demo, nao e copiado 1:1 (tem jitter por pessoa em _sessions_for_persona).
FIAP_PATTERN = [
    ("20:56", 243, Decimal("8.80")),
    ("21:13", 313, Decimal("12.32")),
    ("19:47", 211, Decimal("7.08")),
    ("21:09", 380, Decimal("12.77")),
    ("21:43", 215, Decimal("5.58")),
    ("21:17", 227, Decimal("7.75")),
    ("13:14", 108, Decimal("1.67")),
    ("21:26", 173, Decimal("4.69")),
    ("21:13", 263, Decimal("9.78")),
    ("21:20", 242, Decimal("8.71")),
    ("21:20", 262, Decimal("9.78")),
    ("21:34", 240, Decimal("8.70")),
    ("21:10", 286, Decimal("10.41")),
    ("21:09", 211, Decimal("7.16")),
    ("16:34", 213, Decimal("6.03")),
    ("21:12", 317, Decimal("12.60")),
    ("23:41", 254, Decimal("9.55")),
    ("17:14", 435, Decimal("15.52")),
]

PERSONAS = [
    {
        "email": "marina.alves@chargegrid.demo",
        "name": "Marina Alves",
        "vehicle": "BYD Dolphin Mini",
        "rfid": "RFID-DEMO-0002",
        "sessions": 12,
        "plan": PlanKind.mensal,
    },
    {
        "email": "ricardo.tanaka@chargegrid.demo",
        "name": "Ricardo Tanaka",
        "vehicle": "GWM Ora 03",
        "rfid": "RFID-DEMO-0003",
        "sessions": 9,
        "plan": None,
    },
    {
        "email": "juliana.costa@chargegrid.demo",
        "name": "Juliana Costa",
        "vehicle": "Volvo EX30",
        "rfid": "RFID-DEMO-0004",
        "sessions": 7,
        "plan": None,
    },
    {
        "email": "bruno.ferreira@chargegrid.demo",
        "name": "Bruno Ferreira",
        "vehicle": "Renault Kwid E-Tech",
        "rfid": "RFID-DEMO-0005",
        "sessions": 5,
        "plan": None,
    },
]


def _ensure_tariff_rule(db, establishment_id) -> TariffRule:
    """Estacionamento Central nao tinha nenhuma faixa de tarifa configurada - sem isso as
    sessoes fecham como `error` (skill tarifacao-e-sessoes: sem regra, nao cobra). Mesma
    tarifa flat ja usada nos outros estabelecimentos de demo (R$2,00/kWh), pra nao inventar
    um numero novo."""
    existing = db.query(TariffRule).filter(TariffRule.establishment_id == establishment_id).first()
    if existing is not None:
        return existing
    rule = TariffRule(
        establishment_id=establishment_id,
        name="Unica",
        days_of_week="0,1,2,3,4,5,6",
        start_time_local=time(0, 0),
        end_time_local=time(23, 59, 59),
        price_per_kwh=Decimal("2.0000"),
        is_special=False,
    )
    db.add(rule)
    db.flush()
    return rule


def _sessions_for_persona(persona: dict, today_local) -> list[tuple[datetime, datetime, Decimal]]:
    """Amostra `persona['sessions']` tuplas do padrao da FIAP com jitter deterministico
    (seed derivada do e-mail - mesma pessoa sempre gera o mesmo historico), espalhadas nos
    ultimos HISTORY_DAYS dias. Devolve (inicio_utc, fim_utc, energia_kwh) ordenado no tempo."""
    rng = random.Random(persona["email"])
    count = persona["sessions"]

    pool = list(FIAP_PATTERN)
    rng.shuffle(pool)
    if count <= len(pool):
        chosen = pool[:count]
    else:
        chosen = pool + [rng.choice(FIAP_PATTERN) for _ in range(count - len(pool))]

    days_ago_pool = rng.sample(range(1, HISTORY_DAYS + 1), min(count, HISTORY_DAYS))
    while len(days_ago_pool) < count:
        days_ago_pool.append(rng.randint(1, HISTORY_DAYS))

    sessions = []
    for (start_str, duration_min, energy_kwh), days_ago in zip(chosen, days_ago_pool):
        hour, minute = (int(part) for part in start_str.split(":"))
        jittered_start_minute = minute + rng.randint(-20, 20)
        jittered_duration = max(30, duration_min + rng.randint(-15, 15))
        energy_factor = Decimal(str(round(rng.uniform(0.9, 1.1), 3)))
        jittered_energy = (energy_kwh * energy_factor).quantize(Decimal("0.001"))

        session_date = today_local - timedelta(days=days_ago)
        local_start = datetime.combine(session_date, time(hour, 0), tzinfo=LOCAL_TZ) + timedelta(
            minutes=jittered_start_minute
        )
        local_end = local_start + timedelta(minutes=jittered_duration)
        sessions.append((local_start.astimezone(UTC), local_end.astimezone(UTC), jittered_energy))

    sessions.sort(key=lambda item: item[0])
    return sessions


def _pick_charger(chargers: list[Charger], busy_until: dict, preferred_index: int, start, end):
    """Round-robin a partir do carregador preferido da pessoa, pulando quem ja esta ocupado
    nesse horario - evita duas sessoes de demo simultaneas na mesma vaga fisica."""
    ordered = chargers[preferred_index:] + chargers[:preferred_index]
    for charger in ordered:
        if start >= busy_until.get(charger.id, datetime.min.replace(tzinfo=UTC)):
            busy_until[charger.id] = end
            return charger
    charger = chargers[preferred_index]
    busy_until[charger.id] = max(busy_until.get(charger.id, end), end)
    return charger


def _create_finished_session(
    db, user: User, charger: Charger, establishment_id, start_utc, end_utc, energy_kwh: Decimal
) -> ChargingSession:
    """Mesmo calculo de `services.sessions._finish_session` (tarifa+plano+franquia reais),
    reaproveitado aqui pra nao inventar um valor de sessao por fora do motor de tarifacao."""
    local_start = start_utc.astimezone(LOCAL_TZ)
    tariff_rule = resolve_active_tariff_rule(db, establishment_id, local_start)
    plan_context = _resolve_plan_context(db, user.id, establishment_id)
    duration_minutes = Decimal((end_utc - start_utc).total_seconds()) / Decimal("60")

    result = calculate_session_amount(
        energy_kwh=energy_kwh,
        tariff_rate_per_kwh=tariff_rule.price_per_kwh,
        session_duration_minutes=duration_minutes,
        free_minutes=plan_context.free_minutes,
        plan_discount_pct=plan_context.discount_pct,
        franquia_kwh_available=plan_context.franquia_kwh_available,
    )

    session = ChargingSession(
        user_id=user.id,
        charger_id=charger.id,
        establishment_id=establishment_id,
        status=ChargingSessionStatus.finished,
        started_at=start_utc,
        ended_at=end_utc,
        energy_kwh=energy_kwh,
        amount_due=result.final_amount,
        tariff_rule_id=tariff_rule.id,
        tariff_rate_applied=tariff_rule.price_per_kwh,
        plan_discount_pct=result.plan_discount_pct,
        free_minutes_applied=result.free_minutes_applied,
    )
    db.add(session)
    db.flush()
    return session


def _create_readings_for_session(
    db, charger: Charger, start_utc: datetime, end_utc: datetime, energy_kwh: Decimal
) -> None:
    """Leituras a cada 10 min cobrindo a janela da sessao - so pra alimentar o grafico de
    curva de potencia da tela de detalhe do carregador com historico alem do que o polling
    ao vivo acumulou. Perfil trapezoidal simples (rampa 8% no inicio/fim), nao e telemetria
    real de dispositivo."""
    total_seconds = (end_utc - start_utc).total_seconds()
    if total_seconds <= 0:
        return
    duration_hours = Decimal(total_seconds) / Decimal("3600")
    avg_power_kw = min(charger.nominal_power_kw, energy_kwh / duration_hours)

    # O ambiente de dev tem o polling ao vivo rodando ha tempo - pode ja existir leitura
    # real (charger_id, timestamp) bem nesse minuto. `(charger_id, timestamp)` e unique
    # (idempotencia do polling, ver ChargerReading), entao pula quem ja existe em vez de
    # colidir.
    existing_timestamps = {
        row[0]
        for row in db.query(ChargerReading.timestamp)
        .filter(
            ChargerReading.charger_id == charger.id,
            ChargerReading.timestamp >= start_utc,
            ChargerReading.timestamp <= end_utc,
        )
        .all()
    }

    step = timedelta(minutes=READING_STEP_MINUTES)
    cumulative_energy = Decimal("0.000")
    timestamp = start_utc
    while timestamp <= end_utc:
        fraction = (timestamp - start_utc).total_seconds() / total_seconds
        if fraction < 0.08:
            ramp = Decimal(str(round(fraction / 0.08, 3)))
        elif fraction > 0.92:
            ramp = Decimal(str(round((1 - fraction) / 0.08, 3)))
        else:
            ramp = Decimal("1")
        power_kw = (avg_power_kw * ramp).quantize(Decimal("0.001"))
        cumulative_energy += power_kw * (Decimal(step.total_seconds()) / Decimal("3600"))

        if timestamp not in existing_timestamps:
            status = ChargerStatus.carregando if power_kw > Decimal("0.05") else ChargerStatus.livre
            db.add(
                ChargerReading(
                    charger_id=charger.id,
                    timestamp=timestamp,
                    power_kw=power_kw,
                    status=status,
                    total_energy_kwh=cumulative_energy.quantize(Decimal("0.001")),
                )
            )
        timestamp += step


def run() -> None:
    db = SessionLocal()
    try:
        establishment = (
            db.query(Establishment)
            .join(User, Establishment.owner_id == User.id)
            .filter(User.email == "dono@chargegrid.demo")
            .first()
        )
        if establishment is None:
            print("Estacionamento Central nao encontrado - rode 'python -m app.db.seed' primeiro.")
            return

        chargers = (
            db.query(Charger)
            .filter(Charger.establishment_id == establishment.id)
            .order_by(Charger.spot_label)
            .all()
        )
        if not chargers:
            print(
                "Estacionamento Central sem carregadores - rode "
                "'python -m app.db.seed' primeiro."
            )
            return

        _ensure_tariff_rule(db, establishment.id)
        db.commit()

        today_local = datetime.now(tz=UTC).astimezone(LOCAL_TZ).date()
        busy_until: dict = {}
        created_personas = 0

        for persona_index, persona in enumerate(PERSONAS):
            existing_user = db.query(User).filter(User.email == persona["email"]).first()
            if existing_user is not None:
                print(f"Ja existe: {persona['email']} - pulando (idempotente).")
                continue

            user = User(
                email=persona["email"],
                hashed_password=hash_password("demo1234"),
                full_name=persona["name"],
                role=UserRole.customer,
                vehicle_model=persona["vehicle"],
                rfid_virtual_id=persona["rfid"],
            )
            db.add(user)
            db.flush()

            if persona["plan"] is not None:
                plan = (
                    db.query(Plan)
                    .filter(Plan.establishment_id == establishment.id, Plan.kind == persona["plan"])
                    .one()
                )
                db.add(
                    Subscription(
                        user_id=user.id,
                        plan_id=plan.id,
                        billing_cycle_start=today_local.replace(day=1),
                        billing_cycle_end=None,
                        active=True,
                    )
                )
                db.flush()

            preferred_charger_index = persona_index % len(chargers)
            for start_utc, end_utc, energy_kwh in _sessions_for_persona(persona, today_local):
                charger = _pick_charger(
                    chargers, busy_until, preferred_charger_index, start_utc, end_utc
                )
                _create_finished_session(
                    db, user, charger, establishment.id, start_utc, end_utc, energy_kwh
                )
                _create_readings_for_session(db, charger, start_utc, end_utc, energy_kwh)

            db.commit()
            created_personas += 1
            print(
                f"Criado: {persona['name']} ({persona['email']}) - {persona['sessions']} sessoes."
            )

        print(
            f"Historico de demo aplicado: {created_personas} cliente(s) novo(s) no "
            f"Estacionamento Central ({establishment.id}). PROVISORIO - ver docstring deste "
            "arquivo e tasks/milestones/M11-impacto-goodwe.md."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
