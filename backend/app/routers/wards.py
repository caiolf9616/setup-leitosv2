from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app import crud
from app.database import get_db
from app.dependencies import get_current_credential
from app.models import UserAccount
from app.schemas import WardOut

router = APIRouter(prefix="/api/wards", tags=["wards"])


@router.get("", response_model=list[WardOut])
def list_wards(
    credential: UserAccount = Depends(get_current_credential),
    db: DbSession = Depends(get_db),
):
    """Enfermarias visiveis a qualquer usuario autenticado para consulta."""
    return crud.get_wards(db, unit_groups=None)
