from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app import crud
from app.database import get_db
from app.dependencies import allowed_unit_groups, get_current_credential
from app.models import AuditLog, UserAccount
from app.routers.painel import broadcast_available_beds
from app.schemas import BedBlockUpdate, BedOut

router = APIRouter(prefix="/api/beds", tags=["beds"])


def _bed_out(bed, last_event=None) -> BedOut:
    return BedOut(
        id=bed.id,
        ward_id=bed.ward_id,
        ward_name=bed.ward.display_name,
        unit_group=bed.ward.unit_group,
        number=bed.number,
        blocked=bed.blocked,
        last_event_type=last_event.event_type if last_event else None,
        last_event_at=last_event.occurred_at if last_event else None,
    )


@router.get("", response_model=list[BedOut])
def list_beds(
    ward_id: int | None = None,
    unit_group: str | None = None,
    credential: UserAccount = Depends(get_current_credential),
    db: DbSession = Depends(get_db),
):
    """Consulta autenticada de todos os leitos e seus status atuais.

    Toda unidade pode consultar o panorama completo. A permissao de alterar
    continua restrita no POST /api/events, que valida a unidade do leito.
    """
    pairs = crud.get_beds_with_last_event(
        db, unit_groups={unit_group} if unit_group else None, ward_id=ward_id
    )

    return [
        _bed_out(bed, last_event)
        for bed, last_event in pairs
    ]


@router.patch("/{bed_id}/blocked", response_model=BedOut)
async def update_bed_blocked(
    bed_id: int,
    payload: BedBlockUpdate,
    credential: UserAccount = Depends(get_current_credential),
    db: DbSession = Depends(get_db),
):
    """Bloqueia ou desbloqueia um leito para controle operacional interno."""
    bed = crud.get_bed_or_none(db, bed_id)
    if bed is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Leito nao encontrado")

    unit_groups = allowed_unit_groups(credential)
    if unit_groups is not None and bed.ward.unit_group not in unit_groups:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Leito fora da sua unidade")

    if payload.blocked and not bed.blocked:
        pairs = crud.get_beds_with_last_event(db, unit_groups=None, ward_id=bed.ward_id)
        last_event = next((event for listed_bed, event in pairs if listed_bed.id == bed.id), None)
        if last_event is not None and last_event.event_type.value not in {"apto", "desocupado"}:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Somente leitos sem status, Aptos ou Desocupados podem ser bloqueados",
            )

    if bed.blocked != payload.blocked:
        bed.blocked = payload.blocked
        db.add(
            AuditLog(
                actor_username=credential.username,
                action="bed_blocked" if payload.blocked else "bed_unblocked",
                details=f"Unidade {bed.ward.unit_group}; enfermaria {bed.ward.display_name}; leito {bed.number}",
            )
        )
        db.commit()
        db.refresh(bed)

    pairs = crud.get_beds_with_last_event(db, unit_groups=None, ward_id=bed.ward_id)
    last_event = next((event for listed_bed, event in pairs if listed_bed.id == bed.id), None)
    await broadcast_available_beds()
    return _bed_out(bed, last_event)
