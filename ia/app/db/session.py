from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url)


@event.listens_for(engine, "connect")
def _enforce_read_only(dbapi_connection, connection_record) -> None:
    """Reforca na pratica (nao so por convencao) a regra da skill
    `ml-previsao-e-anomalias`: a IA nunca escreve em tabela transacional. Qualquer INSERT/
    UPDATE acidental falha no proprio Postgres em vez de passar despercebido em code review.

    So aplicavel a Postgres - `DATABASE_URL` apontando para outro dialeto (SQLite em debug
    local, por exemplo) segue sem essa trava."""
    if engine.dialect.name != "postgresql":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("SET default_transaction_read_only = on")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
