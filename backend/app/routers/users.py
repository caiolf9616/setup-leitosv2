"""Gerenciamento de contas individuais, restrito ao administrador."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.auth import hash_password, validate_new_password
from app.database import get_db
from app.dependencies import get_current_credential
from app.models import AuditLog, UserAccount, UserRole, UserSession, Ward
from app.schemas import (
    AuditLogOut, PasswordResetRequest, UserCreate, UserOut,
    UserReplacementRequest, UserUpdate,
)

router = APIRouter(prefix="/api/users", tags=["users"])

EMPLOYMENT_TYPES = {
    "diarista",
    "plantonista",
    "coordenador_unidade",
    "coordenador_geral",
    "administrador",
    "acesso_legado",
}


def _is_administrator(user: UserAccount) -> bool:
    return user.role == UserRole.COORDENADOR and user.employment_type == "administrador"


def _is_unit_coordinator(user: UserAccount) -> bool:
    return user.employment_type == "coordenador_unidade" and user.role == UserRole.UNIDADE


def _is_general_coordinator(user: UserAccount) -> bool:
    return user.employment_type == "coordenador_geral" and user.role == UserRole.COORDENADOR


def _can_manage_all_units(user: UserAccount) -> bool:
    return _is_administrator(user) or _is_general_coordinator(user)


def _audit(db, actor, action, target, details=None):
    db.add(AuditLog(
        actor_username=actor.username,
        action=action,
        target_username=target.username if target else None,
        details=details,
    ))


def _require_target_access(current: UserAccount, user: UserAccount) -> None:
    if not _can_manage_all_units(current) and user.unit_group != current.unit_group:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário sem permissão")
    if not _is_administrator(current) and _is_administrator(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário sem permissão")


def require_user_manager(
    current: UserAccount = Depends(get_current_credential),
) -> UserAccount:
    if not _is_administrator(current):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário sem permissão")
    return current


def _validate_scope(db: DbSession, role: UserRole, unit_group: str, employment_type: str) -> str:
    unit_group = unit_group.strip().upper()
    if employment_type not in EMPLOYMENT_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tipo de vínculo inválido")
    if role == UserRole.COORDENADOR:
        if employment_type not in {"coordenador_geral", "administrador"}:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Coordenação geral exige o vínculo correspondente")
        return "COORDENACAO"
    if unit_group == "COORDENACAO" or not db.query(Ward.id).filter_by(unit_group=unit_group).first():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unidade inválida")
    if employment_type == "coordenador_geral":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Vínculo incompatível com usuário de unidade")
    return unit_group


@router.get("", response_model=list[UserOut])
def list_users(
    current: UserAccount = Depends(require_user_manager),
    db: DbSession = Depends(get_db),
):
    query = db.query(UserAccount)
    if _is_general_coordinator(current):
        query = query.filter(UserAccount.employment_type != "administrador")
    elif not _is_administrator(current):
        query = query.filter(
            UserAccount.unit_group == current.unit_group,
            UserAccount.employment_type != "administrador",
        )
    return query.order_by(UserAccount.active.desc(), UserAccount.full_name).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    current: UserAccount = Depends(require_user_manager),
    db: DbSession = Depends(get_db),
):
    username = payload.username.strip().upper()
    if len(username) < 3 or not payload.full_name.strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe nome e login com pelo menos 3 caracteres",
        )
    password_error = validate_new_password(payload.password)
    if password_error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=password_error)
    if db.query(UserAccount.id).filter_by(username=username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Este login já está em uso")
    try:
        role = UserRole(payload.role)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Perfil inválido") from exc
    if not _is_administrator(current) and payload.employment_type == "administrador":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário sem permissão")
    requested_unit = payload.unit_group if _can_manage_all_units(current) else current.unit_group
    if not _can_manage_all_units(current) and role != UserRole.UNIDADE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário sem permissão")
    unit_group = _validate_scope(db, role, requested_unit, payload.employment_type)
    user = UserAccount(
        username=username,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        unit_group=unit_group,
        role=role,
        employment_type=payload.employment_type,
        active=True,
        must_change_password=True,
    )
    db.add(user)
    _audit(db, current, "user_created", user, "Conta criada com senha temporária")
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current: UserAccount = Depends(require_user_manager),
    db: DbSession = Depends(get_db),
):
    user = db.get(UserAccount, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    _require_target_access(current, user)
    if payload.active is False and user.id == current.id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Você não pode desativar a própria conta")
    if user.id == current.id and any(
        value is not None
        for value in (payload.role, payload.unit_group, payload.employment_type)
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Você não pode alterar o próprio perfil ou escopo de acesso",
        )
    if _is_administrator(user) and (
        payload.active is False
        or (payload.role is not None and payload.role != UserRole.COORDENADOR.value)
        or (payload.unit_group is not None and payload.unit_group.strip().upper() != "COORDENACAO")
        or (payload.employment_type is not None and payload.employment_type != "administrador")
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="A conta Administrador não pode ser desativada ou ter seu perfil alterado",
        )

    try:
        role = UserRole(payload.role) if payload.role is not None else user.role
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Perfil inválido") from exc
    if not _can_manage_all_units(current):
        role = UserRole.UNIDADE
    employment_type = payload.employment_type or user.employment_type
    if not _is_administrator(current) and employment_type == "administrador":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário sem permissão")
    requested_unit = (payload.unit_group or user.unit_group) if _can_manage_all_units(current) else current.unit_group
    unit_group = _validate_scope(db, role, requested_unit, employment_type)
    if payload.full_name is not None:
        if not payload.full_name.strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nome obrigatório")
        user.full_name = payload.full_name.strip()
    user.role = role
    user.unit_group = unit_group
    user.employment_type = employment_type
    if payload.active is not None:
        user.active = payload.active
    if payload.password:
        password_error = validate_new_password(payload.password)
        if password_error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=password_error)
        user.password_hash = hash_password(payload.password)
        user.must_change_password = True

    if payload.password or payload.active is False:
        db.query(UserSession).filter_by(user_id=user.id).delete(synchronize_session=False)
    _audit(db, current, "user_updated", user, "Conta ou acesso atualizado")
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current: UserAccount = Depends(require_user_manager),
    db: DbSession = Depends(get_db),
):
    user = db.get(UserAccount, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    if user.id == current.id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Você não pode excluir a própria conta")
    if _is_administrator(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="A conta Administrador não pode ser excluída")
    _require_target_access(current, user)

    db.query(UserSession).filter_by(user_id=user.id).delete(synchronize_session=False)
    _audit(db, current, "user_deleted", user, "Conta excluída; histórico operacional preservado")
    db.delete(user)
    db.commit()
    return None


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    payload: PasswordResetRequest,
    current: UserAccount = Depends(require_user_manager),
    db: DbSession = Depends(get_db),
):
    user = db.get(UserAccount, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    _require_target_access(current, user)
    password_error = validate_new_password(payload.temporary_password)
    if password_error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=password_error)
    user.password_hash = hash_password(payload.temporary_password)
    user.must_change_password = True
    db.query(UserSession).filter_by(user_id=user.id).delete(synchronize_session=False)
    _audit(db, current, "password_reset", user, "Senha temporária definida; sessões encerradas")
    db.commit()
    return {"ok": True, "must_change_password": True}


@router.post("/{user_id}/replacement", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_replacement(
    user_id: int,
    payload: UserReplacementRequest,
    current: UserAccount = Depends(require_user_manager),
    db: DbSession = Depends(get_db),
):
    source = db.get(UserAccount, user_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    _require_target_access(current, source)
    if _is_administrator(source):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="O Administrador não pode ser substituído")
    username = payload.username.strip().upper()
    if len(username) < 3 or not payload.full_name.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe nome e login válidos")
    if db.query(UserAccount.id).filter_by(username=username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Este login já está em uso")
    password_error = validate_new_password(payload.temporary_password)
    if password_error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=password_error)

    replacement = UserAccount(
        username=username,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.temporary_password),
        unit_group=source.unit_group,
        role=source.role,
        employment_type=source.employment_type,
        active=True,
        must_change_password=True,
    )
    db.add(replacement)
    if payload.deactivate_source:
        source.active = False
        db.query(UserSession).filter_by(user_id=source.id).delete(synchronize_session=False)
    _audit(
        db, current, "user_replaced", replacement,
        f"Perfil copiado de {source.username}; anterior {'desativado' if payload.deactivate_source else 'mantido ativo'}",
    )
    db.commit()
    db.refresh(replacement)
    return replacement


@router.get("/audit/recent", response_model=list[AuditLogOut])
def recent_audit_logs(
    current: UserAccount = Depends(require_user_manager),
    db: DbSession = Depends(get_db),
):
    query = db.query(AuditLog)
    if not _can_manage_all_units(current):
        allowed_users = db.query(UserAccount.username).filter_by(unit_group=current.unit_group)
        query = query.filter(AuditLog.target_username.in_(allowed_users))
    return query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(50).all()
