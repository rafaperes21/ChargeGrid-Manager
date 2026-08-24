import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  garante que todas as tabelas entrem no metadata abaixo
from app.db.session import get_db
from app.main import app
from app.models.base import Base

# SQLite em memoria para os testes: nao depende de Postgres de pe no CI.
# Os tipos usados nos models (Uuid generico, Numeric, Enum) sao portaveis entre dialetos;
# a validacao contra Postgres de verdade (indices, tipos nativos) e feita via
# `alembic upgrade head` em ambiente de desenvolvimento, nao aqui.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def _reset_database():
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def db_session():
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
