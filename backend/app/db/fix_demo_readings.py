"""Corrige o backfill de ChargerReading do historico de demo ja aplicado - as duas versoes
anteriores de `seed_demo_history.py` erravam o odometro do carregador: a primeira zerava
`total_energy_kwh` a cada sessao; a segunda carregava um unico acumulador por carregador do
inicio ao fim, o que diverge do polling ao vivo (que continua rodando em paralelo o mes
inteiro) nos intervalos *entre* sessoes de demo. `_backfill_readings` (versao atual) reancora
em cada sessao individualmente - reaproveitada aqui.

Apaga as leituras dentro da janela exata de cada sessao dos clientes de demo (a sessao em si
e a fonte confiavel de `charger_id`/`started_at`/`ended_at` - nunca muda) e regenera.

Uso: `cd backend && python -m app.db.fix_demo_readings` - idempotente (rodar de novo so
regenera as mesmas leituras), so faz sentido depois de `seed_demo_history.py` ja ter rodado.
"""

from decimal import Decimal

from app.db.seed_demo_history import PERSONAS, _backfill_readings
from app.db.session import SessionLocal
from app.models.charger import Charger, ChargerReading
from app.models.session import ChargingSession
from app.models.user import User

DEMO_EMAILS = [persona["email"] for persona in PERSONAS]


def run() -> None:
    db = SessionLocal()
    try:
        demo_user_ids = [
            row[0] for row in db.query(User.id).filter(User.email.in_(DEMO_EMAILS)).all()
        ]
        if not demo_user_ids:
            print(
                "Nenhum cliente de demo encontrado - rode "
                "'python -m app.db.seed_demo_history' primeiro."
            )
            return

        sessions = (
            db.query(ChargingSession)
            .filter(ChargingSession.user_id.in_(demo_user_ids))
            .order_by(ChargingSession.started_at)
            .all()
        )
        if not sessions:
            print("Nenhuma sessao de demo encontrada.")
            return

        chargers_by_id = {charger.id: charger for charger in db.query(Charger).all()}

        total_deleted = 0
        for session in sessions:
            deleted = (
                db.query(ChargerReading)
                .filter(
                    ChargerReading.charger_id == session.charger_id,
                    ChargerReading.timestamp >= session.started_at,
                    ChargerReading.timestamp <= session.ended_at,
                )
                .delete(synchronize_session=False)
            )
            total_deleted += deleted
        db.flush()

        session_windows = [
            (
                chargers_by_id[session.charger_id],
                session.started_at,
                session.ended_at,
                session.energy_kwh or Decimal("0.000"),
            )
            for session in sessions
        ]
        _backfill_readings(db, session_windows)

        db.commit()
        charger_count = len({session.charger_id for session in sessions})
        print(
            f"Leituras corrigidas: {total_deleted} apagadas e regeneradas com reancoragem "
            f"por sessao em {charger_count} carregador(es)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
