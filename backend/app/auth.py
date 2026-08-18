"""
Autenticacao simples por senha unica de unidade (ou coordenador).

Nao usamos JWT: a sessao fica gravada na tabela `sessions` e o cookie so
carrega o id (aleatorio, opaco) dessa sessao. Isso deixa facil revogar
(ex: "trocar senha da unidade" pode apagar as sessoes antigas) sem precisar
de blacklist de token.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy.orm import Session as DbSession

from app.models import UserAccount, UserSession
from app.settings import get_settings

settings = get_settings()

COOKIE_NAME = "setup_leitos_session"

# Nota: usamos o pacote `bcrypt` direto (nao passlib). A combinacao
# passlib 1.7.x + bcrypt 4.x tem um bug conhecido de deteccao de versao
# (AttributeError: module 'bcrypt' has no attribute '__about__') que quebra
# o hash de senha. Indo direto no bcrypt evitamos essa dependencia extra.
_BCRYPT_MAX_BYTES = 72  # limite do proprio algoritmo bcrypt


def hash_password(raw_password: str) -> str:
    password_bytes = raw_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(raw_password: str, password_hash: str) -> bool:
    password_bytes = raw_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))


def validate_new_password(raw_password: str) -> str | None:
    """Retorna a regra violada ou None quando a senha atende à política."""
    if len(raw_password) < 8:
        return "A senha deve ter pelo menos 8 caracteres"
    if not any(character.isalpha() for character in raw_password):
        return "A senha deve conter pelo menos uma letra"
    if not any(character.isdigit() for character in raw_password):
        return "A senha deve conter pelo menos um número"
    return None


def authenticate(db: DbSession, username: str, raw_password: str) -> UserAccount | None:
    """Retorna a credencial se a senha bater, ou None se usuario/senha invalidos."""
    credential = (
        db.query(UserAccount)
        .filter(UserAccount.username == username.strip().upper())
        .one_or_none()
    )
    if credential is None or not credential.active:
        return None
    if not verify_password(raw_password, credential.password_hash):
        return None
    return credential


def create_session(db: DbSession, credential: UserAccount) -> UserSession:
    """Cria uma sessao nova no banco, valida por SESSION_MAX_AGE_DAYS."""
    now = datetime.now(timezone.utc)
    # Evita crescimento indefinido da tabela sem depender de um job externo.
    db.query(UserSession).filter(UserSession.expires_at < now).delete(
        synchronize_session=False
    )
    expires_at = now + timedelta(days=settings.session_max_age_days)
    session = UserSession(user_id=credential.id, expires_at=expires_at)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_valid_session(db: DbSession, session_id: str) -> UserSession | None:
    session = db.get(UserSession, session_id)
    if session is None:
        return None

    expires_at = session.expires_at
    # SQLite nao guarda timezone e devolve datetime "naive" (usado so em testes
    # locais rapidos); Postgres em producao sempre devolve "aware". Normalizamos
    # aqui pra comparacao nunca quebrar independente do banco.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    return session


def delete_session(db: DbSession, session_id: str) -> None:
    session = db.get(UserSession, session_id)
    if session is not None:
        db.delete(session)
        db.commit()
