from datetime import datetime

from pydantic import BaseModel

from app.models import EventType


class LoginRequest(BaseModel):
    # unit_group mantém compatibilidade com login.js antigo ainda em cache.
    username: str | None = None
    unit_group: str | None = None
    password: str


class CredentialOut(BaseModel):
    username: str
    unit_group: str
    full_name: str
    display_name: str
    role: str
    employment_type: str
    must_change_password: bool

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    unit_group: str
    employment_type: str
    role: str = "unidade"


class UserUpdate(BaseModel):
    full_name: str | None = None
    unit_group: str | None = None
    employment_type: str | None = None
    role: str | None = None
    active: bool | None = None
    password: str | None = None


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    unit_group: str
    employment_type: str
    role: str
    active: bool
    must_change_password: bool

    model_config = {"from_attributes": True}


class PasswordChangeRequest(BaseModel):
    current_password: str | None = None
    new_password: str


class PasswordResetRequest(BaseModel):
    temporary_password: str


class UserReplacementRequest(BaseModel):
    username: str
    full_name: str
    temporary_password: str
    deactivate_source: bool = True


class AuditLogOut(BaseModel):
    id: int
    actor_username: str
    action: str
    target_username: str | None
    details: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WardOut(BaseModel):
    id: int
    name: str
    display_name: str
    unit_group: str

    model_config = {"from_attributes": True}


class BedOut(BaseModel):
    id: int
    ward_id: int
    ward_name: str
    unit_group: str
    number: str
    blocked: bool
    last_event_type: EventType | None = None
    last_event_at: datetime | None = None


class BedBlockUpdate(BaseModel):
    blocked: bool


class EventCreate(BaseModel):
    bed_id: int
    event_type: EventType
    # None = usa a data/hora atual do servidor (equivalente ao checkbox
    # "Usar data e hora atuais" marcado na tela de registro).
    occurred_at: datetime | None = None


class EventOut(BaseModel):
    id: int
    bed_id: int
    event_type: EventType
    occurred_at: datetime
    recorded_by_unit: str
    recorded_by_user: str | None = None

    model_config = {"from_attributes": True}


class RecentEventOut(BaseModel):
    """Evento recente com a identificacao do leito para o dashboard."""

    id: int
    unit_group: str
    ward_name: str
    bed_number: str
    event_type: EventType
    occurred_at: datetime


class AvailableBedOut(BaseModel):
    """Estado visível no painel público (Apto, Desocupado ou Alta)."""

    bed_id: int
    ward_name: str
    unit_group: str
    bed_number: str
    status: EventType
    status_since: datetime
    blocked: bool = False
    # Compatibilidade com clientes antigos que só conheciam leitos aptos.
    apto_since: datetime | None = None


class BedTimeOut(BaseModel):
    """Tempos acumulados de um leito dentro do periodo do relatorio."""

    bed_id: int
    ward_name: str
    number: str
    blocked: bool
    current_status: EventType | None = None
    durations_seconds: dict[str, int]


class BedTimeReportOut(BaseModel):
    start: datetime
    end: datetime
    generated_at: datetime
    total_beds: int
    totals_seconds: dict[str, int]
    beds: list[BedTimeOut]
