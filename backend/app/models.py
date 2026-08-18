"""
Modelos do banco de dados.

Regras importantes:
- Ward.name e o identificador tecnico UNICO (ex: "UCC-01", "D-01").
- Ward.display_name e o nome real exibido (ex: "01") e pode se repetir.
- Um leito sem nenhum BedEvent registrado ainda (last_event_type nulo) NUNCA entra
  na fila do painel de chamada -- isso e resolvido na query do painel, nao aqui.

Novidade da v2:
- UnitCredential guarda a senha (hash) de cada GRUPO de unidade (ex: "UCC", "B", "D"),
  nao por ward individual. Uma unidade pode ter varios wards com prefixos diferentes;
  o campo Ward.unit_group e o que liga um ward ao grupo/credencial correspondente.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EventType(str, enum.Enum):
    ALTA = "alta"
    DESOCUPADO = "desocupado"
    APTO = "apto"
    OCUPADO = "ocupado"


class UserRole(str, enum.Enum):
    UNIDADE = "unidade"
    COORDENADOR = "coordenador"


class Ward(Base):
    """Enfermaria com chave técnica única e nome de exibição."""

    __tablename__ = "wards"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    # Agrupador usado para casar com UnitCredential.unit_group (ex: "UCC", "B", "D").
    unit_group: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    beds: Mapped[list["Bed"]] = relationship(back_populates="ward", cascade="all, delete-orphan")


class Bed(Base):
    """Leito, vinculado a uma ward. (ward_id, number) precisa ser unico."""

    __tablename__ = "beds"
    __table_args__ = (UniqueConstraint("ward_id", "number", name="uq_bed_ward_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ward_id: Mapped[int] = mapped_column(ForeignKey("wards.id", ondelete="CASCADE"), nullable=False)
    number: Mapped[str] = mapped_column(String(20), nullable=False)
    blocked: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ward: Mapped["Ward"] = relationship(back_populates="beds")
    events: Mapped[list["BedEvent"]] = relationship(back_populates="bed", cascade="all, delete-orphan")


class BedEvent(Base):
    """Historico de eventos de status de um leito."""

    __tablename__ = "bed_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    bed_id: Mapped[int] = mapped_column(ForeignKey("beds.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType, name="event_type"), nullable=False)
    # Momento "real" do evento (pode ser retroativo, ver "Usar data e hora atuais" na tela).
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # unit_group de quem registrou (auditoria simples, ja que login e por unidade e nao por pessoa).
    recorded_by_unit: Mapped[str] = mapped_column(String(50), nullable=False)
    recorded_by_user: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bed: Mapped["Bed"] = relationship(back_populates="events")


class UnitCredential(Base):
    """Credencial de login: senha unica por grupo de unidade, ou do coordenador."""

    __tablename__ = "unit_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Para role=coordenador, usar um valor fixo, ex: "COORDENACAO" (nao corresponde a nenhum ward).
    unit_group: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Session(Base):
    """Sessao de login (cookie assinado referencia o id aqui, permite revogar/expirar)."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    credential_id: Mapped[int] = mapped_column(ForeignKey("unit_credentials.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserAccount(Base):
    """Conta individual de acesso ao sistema."""

    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # COORDENACAO para coordenador geral; unidade real para os demais.
    unit_group: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="account_user_role"), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def display_name(self) -> str:
        return self.full_name


class UserSession(Base):
    """Sessão vinculada a uma conta individual."""

    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLog(Base):
    """Registro imutavel de acoes administrativas sensiveis."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_username: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_username: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    details: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
