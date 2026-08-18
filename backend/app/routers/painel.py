"""
Endpoints do painel de chamada -- tela publica de corredor, sem login (so leitura).

Fluxo:
1. painel.html abre GET /api/painel/status uma vez, ao carregar, pra ter a
   lista inicial sem esperar o primeiro evento.
2. Em seguida conecta no WebSocket /ws/painel e fica ouvindo. Toda vez que um
   evento e registrado em /api/events, o router de events chama
   manager.broadcast(...) com a lista atualizada e todo painel conectado
   recebe na hora.
3. Se o WebSocket cair, o frontend deve tentar reconectar (com backoff) e, ao
   reconectar, chamar /api/painel/status de novo pra resincronizar, ja que
   pode ter perdido eventos enquanto estava desconectado.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session as DbSession

from app import crud
from app.database import SessionLocal, get_db
from app.schemas import AvailableBedOut
from app.websocket_manager import manager

router = APIRouter(tags=["painel"])


def _as_utc(value: datetime) -> datetime:
    """SQLite devolve datas sem fuso; eventos são armazenados em UTC."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _serialize_panel_beds(pairs) -> list[dict]:
    return [
        AvailableBedOut(
            bed_id=bed.id,
            ward_name=bed.ward.display_name,
            unit_group=bed.ward.unit_group,
            bed_number=bed.number,
            status=last_event.event_type,
            status_since=_as_utc(last_event.occurred_at),
            blocked=False,
            apto_since=(
                _as_utc(last_event.occurred_at)
                if last_event.event_type.value == "apto"
                else None
            ),
        ).model_dump(mode="json")
        for bed, last_event in pairs
    ]


@router.get("/api/painel/status", response_model=list[AvailableBedOut])
def painel_status(db: DbSession = Depends(get_db)):
    """Estado atual visível (Apto, Desocupado e Alta), sem autenticação."""
    pairs = crud.get_panel_beds(db)
    return _serialize_panel_beds(pairs)


@router.websocket("/ws/painel")
async def painel_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Nao esperamos nada do cliente -- so mantemos a conexao aberta pra
        # poder empurrar (broadcast) atualizacoes. O loop so serve pra
        # detectar quando o cliente desconecta.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def broadcast_available_beds() -> None:
    """Chamado pelo router de events depois de registrar um evento novo.

    Abre sua propria sessao de banco (nao reaproveita a do request de events)
    porque roda de forma independente do ciclo de vida daquele request.
    """
    db = SessionLocal()
    try:
        pairs = crud.get_panel_beds(db)
        await manager.broadcast(
            {
                "type": "leitos_disponiveis",
                "leitos": _serialize_panel_beds(pairs),
            }
        )
    finally:
        db.close()
