"""
Funcoes de acesso ao banco reutilizadas pelos routers.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session as DbSession, joinedload

from app.models import Bed, BedEvent, Ward


def get_wards(db: DbSession, unit_groups: list[str] | None) -> list[Ward]:
    """unit_groups=None significa 'sem restricao' (coordenador)."""
    # Enfermarias antigas sem nenhum leito não devem permanecer nos selects.
    query = db.query(Ward).join(Bed).distinct()
    if unit_groups is not None:
        query = query.filter(Ward.unit_group.in_(unit_groups))
    return query.order_by(Ward.name).all()


def get_beds_with_last_event(
    db: DbSession,
    unit_groups: list[str] | None,
    ward_id: int | None = None,
) -> list[tuple[Bed, BedEvent | None]]:
    """Retorna [(bed, ultimo_evento_ou_None), ...] respeitando o filtro de unidade.

    Um leito sem nenhum evento ainda volta com ultimo_evento=None -- e assim
    que o resto do sistema (relatorio, painel) sabe que ele esta "Sem Status"
    e nao deve ser tratado como disponivel.
    """
    query = db.query(Bed).options(joinedload(Bed.ward))
    if unit_groups is not None:
        query = query.join(Ward).filter(Ward.unit_group.in_(unit_groups))
    if ward_id is not None:
        query = query.filter(Bed.ward_id == ward_id)
    beds = query.order_by(Bed.ward_id, Bed.number).all()

    if not beds:
        return []

    bed_ids = [b.id for b in beds]
    # Todos os eventos desses leitos, mais recente primeiro; ficamos so com o
    # primeiro que aparece por bed_id (== o mais recente daquele leito).
    events = (
        db.query(BedEvent)
        .filter(BedEvent.bed_id.in_(bed_ids))
        .order_by(BedEvent.bed_id, BedEvent.occurred_at.desc(), BedEvent.id.desc())
        .all()
    )
    latest_by_bed: dict[int, BedEvent] = {}
    for event in events:
        latest_by_bed.setdefault(event.bed_id, event)

    return [(bed, latest_by_bed.get(bed.id)) for bed in beds]


def get_available_beds(db: DbSession) -> list[tuple[Bed, BedEvent]]:
    """Leitos cujo ultimo evento e APTO -- e a fila que o painel de chamada exibe.

    Segue a mesma regra da v1: leito sem nenhum evento (last_event=None) nunca
    entra aqui, e leito bloqueado tambem fica de fora mesmo se o ultimo evento
    registrado tiver sido "apto".
    """
    from app.models import EventType  # import local pra evitar ciclo no topo do arquivo

    pairs = get_beds_with_last_event(db, unit_groups=None)
    return [
        (bed, last_event)
        for bed, last_event in pairs
        if last_event is not None and last_event.event_type == EventType.APTO and not bed.blocked
    ]


def get_panel_beds(db: DbSession) -> list[tuple[Bed, BedEvent]]:
    """Estado lateral do painel: Apto, Desocupado e Alta, sem duplicados.

    `blocked` tem prioridade sobre o último evento. Leitos sem evento e todos
    os demais estados permanecem ocultos.
    """
    from app.models import EventType

    visible_statuses = {
        EventType.APTO,
        EventType.DESOCUPADO,
        EventType.ALTA,
    }
    pairs = get_beds_with_last_event(db, unit_groups=None)
    unique: dict[int, tuple[Bed, BedEvent]] = {}
    for bed, last_event in pairs:
        if (
            bed.blocked
            or last_event is None
            or last_event.event_type not in visible_statuses
        ):
            continue
        unique[bed.id] = (bed, last_event)
    return list(unique.values())


def get_bed_or_none(db: DbSession, bed_id: int) -> Bed | None:
    return db.query(Bed).options(joinedload(Bed.ward)).filter(Bed.id == bed_id).one_or_none()


def create_bed_event(
    db: DbSession,
    bed: Bed,
    event_type,
    occurred_at: datetime | None,
    recorded_by_unit: str,
    recorded_by_user: str,
) -> BedEvent:
    event = BedEvent(
        bed_id=bed.id,
        event_type=event_type,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        recorded_by_unit=recorded_by_unit,
        recorded_by_user=recorded_by_user,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
