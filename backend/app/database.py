"""
Configuracao da conexao com o banco de dados (PostgreSQL).

Para desenvolvimento local, basta ter um Postgres rodando e ajustar
DATABASE_URL no arquivo .env (copie de .env.example).
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.settings import get_settings

settings = get_settings()

database_url = settings.database_url
if database_url.startswith("sqlite"):
    engine = create_engine(database_url, future=True)
else:
    if not database_url.startswith("postgresql"):
        raise RuntimeError(
            "DATABASE_URL deve apontar para PostgreSQL ou SQLite. "
            "Use backend/.env para configurar o ambiente local."
        )
    engine = create_engine(database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Classe base para todos os modelos ORM."""


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI: abre uma sessao por request e garante o fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
