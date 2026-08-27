"""Maquina de estados da sessao de carregamento (M3) - skill `tarifacao-e-sessoes` secao 6.

    pending -> active -> finished
                       \\-> error

- pending: RFID aproximado, aguardando o carregador reportar potencia > 0. Timeout de
  5 min sem potencia -> error, sem cobranca.
- active: acumula energy_kwh a cada leitura do polling, por trapezio (mesma formula do
  simulador, `services/energy_integration.py`).
- finished: potencia zerada em `_END_ZERO_READINGS_THRESHOLD` leituras consecutivas.
  Fecha aplicando o motor de calculo puro (`services/pricing.py`) e grava o snapshot.
- error: sem cobranca, independente do motivo.

`sync_session` e a unica funcao que avanca o estado, e e idempotente: pode ser chamada de
novo a qualquer momento (ex.: toda vez que a tela do cliente consulta a sessao atual) porque
sempre reconstroi o estado a partir das leituras persistidas, usando o timestamp de cada
leitura como chave - nunca o momento em que foi processada (skill, secao 6).

Depende do M2 manter `Charger.status` atualizado pelo polling; por ora (M2 ainda em lote),
quem cria dados de teste precisa setar o status manualmente antes de abrir uma sessao.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.charger import Charger, ChargerReading
from app.models.enums import ChargerStatus, ChargingSessionStatus
from app.models.session import ChargingSession
from app.models.tariff import Plan
from app.models.user import Subscription, User
from app.services import queue
from app.services.energy_integration import trapezoidal_energy_kwh
from app.services.pricing import calculate_session_amount
from app.services.tariffs import resolve_active_tariff_rule

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
PENDING_TIMEOUT = timedelta(minutes=5)

# "N leituras consecutivas" nao tem numero definido na skill - 2 e um default de engenharia,
# nao um valor confirmado com o time; ajustar se o polling real (M2) mostrar ruido demais.
END_ZERO_READINGS_THRESHOLD = 2
ZERO_POWER_THRESHOLD_KW = Decimal("0.050")


def _as_utc(value: datetime) -> datetime:
    """SQLite (usado nos testes) nao preserva tzinfo em `DateTime(timezone=True)` -
    devolve naive na leitura, mesmo o valor tendo sido salvo com timezone. Postgres (prod)
    preserva. Normaliza pra UTC nos dois casos - convencao do projeto e tudo em UTC no banco."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def start_session(db: Session, user: User, charger_id: uuid.UUID) -> ChargingSession:
    charger = db.get(Charger, charger_id)
    if charger is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Carregador nao encontrado"
        )

    if user.rfid_virtual_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario sem cartao RFID virtual cadastrado",
        )

    has_open_session = (
        db.query(ChargingSession)
        .filter(
            ChargingSession.user_id == user.id,
            ChargingSession.status.in_(
                [ChargingSessionStatus.pending, ChargingSessionStatus.active]
            ),
        )
        .first()
        is not None
    )
    if has_open_session:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Usuario ja tem uma sessao em andamento"
        )

    reservation = None
    if charger.status != ChargerStatus.livre:
        # nao livre pode ainda assim ser deste cliente: a fila (services/queue.py) reservou
        # esse carregador especificamente pra ele por 15 min depois que vagou. So consome a
        # reserva depois de garantir que a sessao vai mesmo ser criada (nenhum erro abaixo).
        reservation = queue.find_active_reservation(db, user.id, charger.id)
        if reservation is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Carregador nao esta livre"
            )

    session = ChargingSession(
        user_id=user.id,
        charger_id=charger.id,
        establishment_id=charger.establishment_id,
        status=ChargingSessionStatus.pending,
        started_at=datetime.now(UTC),
    )
    db.add(session)
    # "reservado" prende a vaga assim que o RFID e aceito, pra dois clientes nao
    # disputarem o mesmo carregador enquanto a sessao ainda esta pending. E o mesmo valor
    # que a fila usa pra segurar vaga liberada - por isso o caminho acima confere se a
    # reserva "reservado" e mesmo deste cliente antes de aceitar.
    charger.status = ChargerStatus.reservado
    if reservation is not None:
        queue.consume_reservation(db, reservation)
    db.commit()
    db.refresh(session)
    return session


def _readings_since(db: Session, charger_id: uuid.UUID, since: datetime) -> list[ChargerReading]:
    return (
        db.query(ChargerReading)
        .filter(ChargerReading.charger_id == charger_id, ChargerReading.timestamp >= since)
        .order_by(ChargerReading.timestamp.asc())
        .all()
    )


def _accumulate_energy_kwh(readings: list[ChargerReading]) -> Decimal:
    energy = Decimal("0.000")
    for previous, current in zip(readings, readings[1:]):
        elapsed_hours = Decimal(
            (current.timestamp - previous.timestamp).total_seconds()
        ) / Decimal("3600")
        if elapsed_hours <= 0:
            continue
        energy += trapezoidal_energy_kwh(previous.power_kw, current.power_kw, elapsed_hours)
    return energy


def _ended_by_zero_power(readings: list[ChargerReading]) -> bool:
    if len(readings) < END_ZERO_READINGS_THRESHOLD:
        return False
    tail = readings[-END_ZERO_READINGS_THRESHOLD:]
    return all(r.power_kw <= ZERO_POWER_THRESHOLD_KW for r in tail)


def _franquia_kwh_available(
    db: Session, user_id: uuid.UUID, plan: Plan, cycle_start: date, cycle_end: date | None
) -> Decimal:
    if not plan.free_kwh_allowance:
        return Decimal("0.000")

    finished_sessions = (
        db.query(ChargingSession)
        .filter(
            ChargingSession.user_id == user_id,
            ChargingSession.establishment_id == plan.establishment_id,
            ChargingSession.status == ChargingSessionStatus.finished,
        )
        .all()
    )
    used_kwh = Decimal("0.000")
    for prior in finished_sessions:
        session_date = _as_utc(prior.started_at).astimezone(LOCAL_TZ).date()
        if session_date < cycle_start:
            continue
        if cycle_end is not None and session_date > cycle_end:
            continue
        used_kwh += prior.energy_kwh or Decimal("0")

    return max(plan.free_kwh_allowance - used_kwh, Decimal("0.000"))


@dataclass(frozen=True)
class _PlanContext:
    discount_pct: Decimal
    franquia_kwh_available: Decimal
    free_minutes: int


def _resolve_plan_context(
    db: Session, user_id: uuid.UUID, establishment_id: uuid.UUID
) -> _PlanContext:
    subscription = (
        db.query(Subscription)
        .join(Plan, Subscription.plan_id == Plan.id)
        .filter(
            Subscription.user_id == user_id,
            Subscription.active.is_(True),
            Plan.establishment_id == establishment_id,
        )
        .first()
    )
    if subscription is None:
        # sem assinatura ativa == avulso: sem desconto, sem franquia.
        return _PlanContext(Decimal("0"), Decimal("0.000"), 0)

    plan = subscription.plan
    franquia = _franquia_kwh_available(
        db, user_id, plan, subscription.billing_cycle_start, subscription.billing_cycle_end
    )
    # TODO(M3): minutos gratuitos condicionais (ex. "1a meia hora gratis no fim de semana")
    # ainda nao tem modelo de regra - item em aberto no CRUD de tarifas. Ate existir, 0.
    return _PlanContext(plan.discount_pct or Decimal("0"), franquia, 0)


def _release_charger(db: Session, charger_id: uuid.UUID) -> None:
    charger = db.get(Charger, charger_id)
    if charger is not None:
        charger.status = ChargerStatus.livre
        queue.offer_charger(db, charger)


def _finalize_as_error(db: Session, session: ChargingSession, ended_at: datetime) -> None:
    session.status = ChargingSessionStatus.error
    session.ended_at = ended_at
    _release_charger(db, session.charger_id)


def _finish_session(
    db: Session, session: ChargingSession, readings: list[ChargerReading]
) -> None:
    ended_at = _as_utc(readings[-1].timestamp)
    started_at = _as_utc(session.started_at)
    local_started_at = started_at.astimezone(LOCAL_TZ)

    tariff_rule = resolve_active_tariff_rule(db, session.establishment_id, local_started_at)
    if tariff_rule is None:
        # sem tarifa configurada para o horario de inicio - nao da pra cobrar direito,
        # e melhor nao cobrar do que inventar um preco. Fica pro dono resolver o buraco
        # na grade de tarifas (skill tarifacao-e-sessoes, secao 2).
        _finalize_as_error(db, session, ended_at)
        return

    plan_context = _resolve_plan_context(db, session.user_id, session.establishment_id)
    duration_minutes = Decimal((ended_at - started_at).total_seconds()) / Decimal("60")

    result = calculate_session_amount(
        energy_kwh=session.energy_kwh or Decimal("0.000"),
        tariff_rate_per_kwh=tariff_rule.price_per_kwh,
        session_duration_minutes=duration_minutes,
        free_minutes=plan_context.free_minutes,
        plan_discount_pct=plan_context.discount_pct,
        franquia_kwh_available=plan_context.franquia_kwh_available,
    )

    session.status = ChargingSessionStatus.finished
    session.ended_at = ended_at
    session.tariff_rule_id = tariff_rule.id
    session.tariff_rate_applied = tariff_rule.price_per_kwh
    session.plan_discount_pct = result.plan_discount_pct
    session.free_minutes_applied = result.free_minutes_applied
    session.amount_due = result.final_amount
    _release_charger(db, session.charger_id)


def estimate_live_amount(db: Session, session: ChargingSession, now: datetime) -> Decimal | None:
    """Estimativa do valor acumulado de uma sessao `active`, pra tela do cliente mostrar
    algo alem de kWh enquanto carrega - nunca extrapolado no frontend (skill `ui-dois-portais`).
    Mesma tarifa/plano/franquia que `_finish_session` usaria se a sessao fechasse agora; `None`
    se nao houver regra de tarifa pro horario de inicio (mesmo caso que vira `error` no fechamento
    real - melhor nao estimar do que inventar um preco)."""
    started_at = _as_utc(session.started_at)
    local_started_at = started_at.astimezone(LOCAL_TZ)

    tariff_rule = resolve_active_tariff_rule(db, session.establishment_id, local_started_at)
    if tariff_rule is None:
        return None

    plan_context = _resolve_plan_context(db, session.user_id, session.establishment_id)
    duration_minutes = Decimal((now - started_at).total_seconds()) / Decimal("60")

    result = calculate_session_amount(
        energy_kwh=session.energy_kwh or Decimal("0.000"),
        tariff_rate_per_kwh=tariff_rule.price_per_kwh,
        session_duration_minutes=duration_minutes,
        free_minutes=plan_context.free_minutes,
        plan_discount_pct=plan_context.discount_pct,
        franquia_kwh_available=plan_context.franquia_kwh_available,
    )
    return result.final_amount


def sync_session(db: Session, session: ChargingSession) -> ChargingSession:
    if session.status not in (ChargingSessionStatus.pending, ChargingSessionStatus.active):
        return session  # finished/error sao terminais

    now = datetime.now(UTC)
    started_at = _as_utc(session.started_at)
    readings = _readings_since(db, session.charger_id, session.started_at)

    if session.status == ChargingSessionStatus.pending:
        has_power = any(r.power_kw > ZERO_POWER_THRESHOLD_KW for r in readings)
        if has_power:
            session.status = ChargingSessionStatus.active
            charger = db.get(Charger, session.charger_id)
            if charger is not None:
                charger.status = ChargerStatus.carregando
        elif now - started_at >= PENDING_TIMEOUT:
            _finalize_as_error(db, session, now)
            db.commit()
            db.refresh(session)
            return session
        else:
            return session  # ainda esperando o carregador reportar potencia

    # session.status == active neste ponto (por transicao acima ou ja vinha assim)
    session.energy_kwh = _accumulate_energy_kwh(readings)
    if _ended_by_zero_power(readings):
        _finish_session(db, session, readings)

    db.commit()
    db.refresh(session)
    return session


def build_receipt(session: ChargingSession) -> dict:
    """Recibo digital com a decomposicao bruto -> promocao -> desconto -> franquia -> total
    (skill `tarifacao-e-sessoes`), reconstruida a partir do snapshot ja persistido - nunca
    reprocessada contra tariff_rules/plans atuais (CLAUDE.md), so a aritmetica de
    `pricing.calculate_session_amount` reaplicada aos mesmos numeros congelados no fechamento.

    O valor de franquia usada em R$ nao foi persistido (so o resultado final, `amount_due`) -
    recalculamos o valor SEM franquia e tiramos a diferenca contra o `amount_due` real, que ja
    inclui a franquia que de fato foi aplicada. Isso nunca inventa numero: cada componente vem
    de uma coluna persistida ou de subtracao entre dois valores persistidos/recalculados.
    """
    if session.status != ChargingSessionStatus.finished:
        raise ValueError("So sessoes finalizadas tem recibo")

    duration_minutes = Decimal(
        (_as_utc(session.ended_at) - _as_utc(session.started_at)).total_seconds()
    ) / Decimal("60")

    without_franquia = calculate_session_amount(
        energy_kwh=session.energy_kwh or Decimal("0.000"),
        tariff_rate_per_kwh=session.tariff_rate_applied,
        session_duration_minutes=duration_minutes,
        free_minutes=session.free_minutes_applied or 0,
        plan_discount_pct=session.plan_discount_pct or Decimal("0"),
        franquia_kwh_available=Decimal("0"),
    )
    promo_value = without_franquia.promo_kwh_deducted * session.tariff_rate_applied
    amount_after_promo = without_franquia.gross_amount - promo_value
    amount_after_discount = without_franquia.final_amount
    discount_value = amount_after_promo - amount_after_discount
    # residual: a diferenca entre "sem franquia" e o amount_due real e a franquia de fato
    # aplicada no fechamento. Nao pode ser negativo - se for, e sinal de sessao antiga com dado
    # inconsistente, nao um valor real a mostrar.
    franquia_value = max(Decimal("0.0000"), amount_after_discount - session.amount_due)

    return {
        "session_id": str(session.id),
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "energy_kwh": str(session.energy_kwh),
        "tariff_rate_applied": str(session.tariff_rate_applied),
        "plan_discount_pct": str(session.plan_discount_pct),
        "free_minutes_applied": session.free_minutes_applied,
        "amount_due": str(session.amount_due),
        "gross_amount": str(without_franquia.gross_amount),
        "promo_value": str(promo_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
        "discount_value": str(discount_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
        "franquia_value": str(franquia_value),
        "final_amount": str(session.amount_due),
    }
