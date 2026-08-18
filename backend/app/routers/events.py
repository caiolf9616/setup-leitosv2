from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as DbSession, joinedload

from app import crud
from app.database import get_db
from app.dependencies import allowed_unit_groups, get_current_credential
from app.models import Bed, BedEvent, EventType, UserAccount
from app.routers.painel import broadcast_available_beds
from app.schemas import EventCreate, EventOut, RecentEventOut

router = APIRouter(prefix="/api/events", tags=["events"])

NEXT_STATUS = {
    EventType.OCUPADO: EventType.ALTA,
    EventType.ALTA: EventType.DESOCUPADO,
    EventType.DESOCUPADO: EventType.APTO,
    EventType.APTO: EventType.OCUPADO,
}


def _validate_status_flow(db: DbSession, bed_id: int, event_type: EventType, occurred_at: datetime) -> None:
    """Impede saltos de etapa, inclusive ao inserir movimentações retroativas."""
    previous = (
        db.query(BedEvent)
        .filter(BedEvent.bed_id == bed_id, BedEvent.occurred_at <= occurred_at)
        .order_by(BedEvent.occurred_at.desc(), BedEvent.id.desc())
        .first()
    )
    following = (
        db.query(BedEvent)
        .filter(BedEvent.bed_id == bed_id, BedEvent.occurred_at > occurred_at)
        .order_by(BedEvent.occurred_at, BedEvent.id)
        .first()
    )
    if previous is not None and NEXT_STATUS[previous.event_type] != event_type:
        expected = NEXT_STATUS[previous.event_type].value
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Após {previous.event_type.value}, o próximo status deve ser {expected}",
        )
    if following is not None and NEXT_STATUS[event_type] != following.event_type:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="A movimentação retroativa conflita com o status seguinte do leito",
        )


def _as_utc(value: datetime) -> datetime:
    """SQLite devolve datas sem fuso; os eventos são armazenados em UTC."""
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


@router.get("/recent", response_model=list[RecentEventOut])
def list_recent_events(
    limit: int = Query(default=5, ge=1, le=20),
    credential: UserAccount = Depends(get_current_credential),
    db: DbSession = Depends(get_db),
):
    """Retorna as ultimas movimentacoes reais, inclusive repetidas no mesmo leito."""
    del credential
    events = (
        db.query(BedEvent)
        .options(joinedload(BedEvent.bed).joinedload(Bed.ward))
        .order_by(BedEvent.occurred_at.desc(), BedEvent.id.desc())
        .limit(limit)
        .all()
    )
    return [
        RecentEventOut(
            id=event.id,
            unit_group=event.bed.ward.unit_group,
            ward_name=event.bed.ward.display_name,
            bed_number=event.bed.number,
            event_type=event.event_type,
            occurred_at=_as_utc(event.occurred_at),
        )
        for event in events
    ]


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    credential: UserAccount = Depends(get_current_credential),
    db: DbSession = Depends(get_db),
):
    """Registra um evento de status (alta/desocupado/apto/ocupado) num leito.

    So permite registrar em leito da propria unidade -- mesmo que alguem tente
    forjar um bed_id de outro setor direto na API, o backend barra aqui.
    Coordenador pode registrar em qualquer leito.
    """
    bed = crud.get_bed_or_none(db, payload.bed_id)
    if bed is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Leito nao encontrado")

    unit_groups = allowed_unit_groups(credential)
    if unit_groups is not None and bed.ward.unit_group not in unit_groups:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Leito fora da sua unidade")

    if bed.blocked:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Leito bloqueado, nao aceita novos eventos")

    occurred_at = _as_utc(payload.occurred_at or datetime.now(timezone.utc))
    _validate_status_flow(db, bed.id, payload.event_type, occurred_at)

    event = crud.create_bed_event(
        db,
        bed=bed,
        event_type=payload.event_type,
        occurred_at=occurred_at,
        recorded_by_unit=credential.unit_group,
        recorded_by_user=credential.username,
    )

    # Empurra a lista atualizada de leitos disponiveis pra quem estiver com o
    # painel de chamada aberto. Sempre dispara (nao so quando vira "apto"):
    # e barato, mantem o codigo simples, e cobre tambem o caso de um leito
    # SAIR da lista (ex: virou "ocupado" logo depois de "apto").
    await broadcast_available_beds()

    return event
