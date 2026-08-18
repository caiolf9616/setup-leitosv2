"""
Gerenciador de conexoes WebSocket do painel de chamada.

Como a v2 roda tudo num processo so, o broadcast e uma chamada direta em
memoria -- nao tem HTTP nem fila externa envolvida. Se um dia o servico
precisar rodar em mais de um processo/worker (ex: multiplos workers do
uvicorn/gunicorn), esse manager teria que virar algo compartilhado (Redis
pub/sub, por exemplo); pra uma unica VM com um processo, isso aqui basta.
"""
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Painel conectado (%d ativos)", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("Painel desconectado (%d ativos)", len(self.active_connections))

    async def broadcast(self, payload: dict) -> None:
        """Envia o payload pra todo painel conectado. Remove quem cair no meio do caminho."""
        conexoes_mortas: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(payload)
            except Exception:
                conexoes_mortas.append(connection)

        for connection in conexoes_mortas:
            self.disconnect(connection)


# Singleton do processo -- importado tanto pelo router do painel (que aceita
# as conexoes) quanto pelo router de events (que dispara o broadcast).
manager = ConnectionManager()
