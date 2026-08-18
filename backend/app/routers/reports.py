"""Relatorios analiticos baseados no historico de eventos dos leitos."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DbSession, joinedload

from app.database import get_db
from app.dependencies import allowed_unit_groups, get_current_credential
from app.models import Bed, BedEvent, EventType, UserAccount, Ward
from app.schemas import BedTimeOut, BedTimeReportOut

router = APIRouter(prefix="/api/reports", tags=["reports"])

STATUS_KEYS = [status.value for status in EventType]


def _as_utc(value: datetime) -> datetime:
    """Normaliza para UTC, inclusive em bancos legados com data sem fuso."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@router.get("/bed-times", response_model=BedTimeReportOut)
def bed_times_report(
    start: datetime = Query(..., description="Inicio do periodo (ISO 8601)."),
    end: datetime = Query(..., description="Fim do periodo (ISO 8601)."),
    ward_id: int | None = None,
    unit_group: str | None = None,
    credential: UserAccount = Depends(get_current_credential),
    db: DbSession = Depends(get_db),
):
    """Soma quanto tempo cada leito permaneceu em cada status no periodo."""
    # A consulta é institucional para todos os perfis; somente a escrita de
    # eventos é limitada à unidade do profissional.
    unit_groups = None
    start, end = _as_utc(start), _as_utc(end)
    now = datetime.now(timezone.utc)
    # A tela envia 23:59:59 quando o período termina hoje. O relatório deve
    # medir tempo já transcorrido, nunca projetar o status até o fim do dia.
    end = min(end, now)
    if end <= start:
        raise HTTPException(
            status_code=422,
            detail="O período precisa começar antes do horário atual.",
        )

    beds_query = db.query(Bed).options(joinedload(Bed.ward)).join(Ward).order_by(Bed.ward_id, Bed.number)
    if ward_id is not None:
        beds_query = beds_query.filter(Bed.ward_id == ward_id)
    if unit_group is not None:
        beds_query = beds_query.filter(Ward.unit_group == unit_group)
    if unit_groups is not None:
        beds_query = beds_query.filter(Ward.unit_group.in_(unit_groups))
    beds = beds_query.all()
    bed_ids = [bed.id for bed in beds]
    events_by_bed: dict[int, list[BedEvent]] = {bed_id: [] for bed_id in bed_ids}

    if bed_ids:
        events = (
            db.query(BedEvent)
            .filter(BedEvent.bed_id.in_(bed_ids), BedEvent.occurred_at <= end)
            .order_by(BedEvent.bed_id, BedEvent.occurred_at, BedEvent.id)
            .all()
        )
        for event in events:
            events_by_bed[event.bed_id].append(event)

    totals = {key: 0 for key in STATUS_KEYS}
    rows: list[BedTimeOut] = []
    for bed in beds:
        durations = {key: 0 for key in STATUS_KEYS}
        current_status: str | None = None
        cursor = start

        for event in events_by_bed[bed.id]:
            event_at = _as_utc(event.occurred_at)
            if event_at <= start:
                current_status = event.event_type.value
                continue

            if current_status is not None:
                durations[current_status] += max(0, int((event_at - cursor).total_seconds()))
            current_status = event.event_type.value
            cursor = event_at

        if current_status is not None:
            durations[current_status] += max(0, int((end - cursor).total_seconds()))

        for status, seconds in durations.items():
            totals[status] += seconds
        rows.append(BedTimeOut(
            bed_id=bed.id,
            ward_name=bed.ward.display_name,
            number=bed.number,
            blocked=bed.blocked,
            current_status=EventType(current_status) if current_status else None,
            durations_seconds=durations,
        ))

    return BedTimeReportOut(
        start=start,
        end=end,
        generated_at=now,
        total_beds=len(beds),
        totals_seconds=totals,
        beds=rows,
    )
