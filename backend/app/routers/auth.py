from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DbSession

from app.auth import (
    COOKIE_NAME,
    authenticate,
    create_session,
    delete_session,
    hash_password,
    validate_new_password,
    verify_password,
)
from app.database import get_db
from app.dependencies import get_current_credential
from app.login_limiter import LoginRateLimiter
from app.models import AuditLog, UserAccount, UserSession
from app.schemas import CredentialOut, LoginRequest, PasswordChangeRequest
from app.settings import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()
login_limiter = LoginRateLimiter(
    max_attempts=settings.login_max_attempts,
    window_seconds=settings.login_window_seconds,
)


@router.post("/login", response_model=CredentialOut)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession = Depends(get_db),
):
    login_name = payload.username or payload.unit_group
    if not login_name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe o login")
    normalized_login = login_name.strip().upper()
    client_host = request.client.host if request.client else "unknown"
    limiter_key = f"{client_host}:{normalized_login}"
    if login_limiter.is_blocked(limiter_key):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Aguarde 5 minutos e tente novamente.",
            headers={"Retry-After": str(settings.login_window_seconds)},
        )

    credential = authenticate(db, login_name, payload.password)
    if credential is None:
        login_limiter.record_failure(limiter_key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Login ou senha inválidos")

    login_limiter.reset(limiter_key)
    session = create_session(db, credential)

    # httponly: JS nao consegue ler o cookie (protege contra XSS roubando a sessao)
    # secure=True: exige HTTPS em producao. Em dev local (http://localhost) o navegador
    # aceita normalmente pois localhost e tratado como "contexto seguro".
    response.set_cookie(
        key=COOKIE_NAME,
        value=session.id,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_max_age_days * 24 * 60 * 60,
        path="/",
    )
    return credential


@router.post("/logout")
def logout(request: Request, response: Response, db: DbSession = Depends(get_db)):
    session_id = request.cookies.get(COOKIE_NAME)
    if session_id:
        delete_session(db, session_id)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=CredentialOut)
def me(credential: UserAccount = Depends(get_current_credential)):
    """Usado pelo frontend pra saber se a sessao ainda e valida e quem esta logado."""
    return credential


@router.post("/change-password")
def change_password(
    payload: PasswordChangeRequest,
    response: Response,
    credential: UserAccount = Depends(get_current_credential),
    db: DbSession = Depends(get_db),
):
    if not credential.must_change_password:
        if not payload.current_password or not verify_password(
            payload.current_password, credential.password_hash
        ):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Senha atual invalida")
    password_error = validate_new_password(payload.new_password)
    if password_error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=password_error)
    if verify_password(payload.new_password, credential.password_hash):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A nova senha precisa ser diferente da senha atual",
        )

    credential.password_hash = hash_password(payload.new_password)
    credential.must_change_password = False
    # Encerra todas as sessoes; o usuario entra novamente com a senha pessoal.
    db.query(UserSession).filter_by(user_id=credential.id).delete(synchronize_session=False)
    db.add(AuditLog(
        actor_username=credential.username,
        action="password_changed",
        target_username=credential.username,
        details="Senha alterada pelo proprio usuario",
    ))
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}
