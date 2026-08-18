"""
Dependencies de autenticacao/autorizacao usadas nas rotas protegidas.

Uso tipico num router:

    @router.get("/api/beds")
    def list_beds(credential: UnitCredential = Depends(get_current_credential), db=Depends(get_db)):
        ...

    @router.get("/api/reports")
    def reports(credential: UnitCredential = Depends(require_coordenador), db=Depends(get_db)):
        ...  # so coordenador passa
"""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DbSession

from app.auth import COOKIE_NAME, get_valid_session
from app.database import get_db
from app.models import UserAccount, UserRole


def get_current_credential(
    request: Request,
    db: DbSession = Depends(get_db),
) -> UserAccount:
    """Le o cookie de sessao, valida e retorna a credencial (unidade ou coordenador).

    Lanca 401 se nao houver sessao valida -- o frontend deve redirecionar pro /login.
    """
    session_id = request.cookies.get(COOKIE_NAME)
    if not session_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Nao autenticado")

    session = get_valid_session(db, session_id)
    if session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Sessao invalida ou expirada")

    credential = db.get(UserAccount, session.user_id)
    if credential is None or not credential.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Sessao invalida")

    if credential.must_change_password and request.url.path not in {
        "/api/auth/me",
        "/api/auth/change-password",
        "/api/auth/logout",
    }:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Troca de senha obrigatoria",
        )

    return credential


def require_coordenador(
    credential: UserAccount = Depends(get_current_credential),
) -> UserAccount:
    """Mesma coisa que get_current_credential, mas exige perfil Coordenador."""
    if credential.role != UserRole.COORDENADOR:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao coordenador")
    return credential


def allowed_unit_groups(credential: UserAccount) -> list[str] | None:
    """None significa 'sem restricao' (coordenador ve tudo). Lista = so esses grupos."""
    if credential.role == UserRole.COORDENADOR:
        return None
    return [credential.unit_group]
