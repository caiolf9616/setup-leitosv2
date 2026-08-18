"""
Ponto de entrada da aplicacao.

Rodar em dev:
    cd backend
    uvicorn app.main:app --reload --port 8000
"""
import mimetypes
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from app.database import get_db

from app.routers import auth as auth_router
from app.routers import beds as beds_router
from app.routers import events as events_router
from app.routers import painel as painel_router
from app.routers import reports as reports_router
from app.routers import wards as wards_router
from app.routers import users as users_router

app = FastAPI(title="Setup de Leitos v2")

# O registro padrão do Windows nem sempre reconhece fontes web. Com
# X-Content-Type-Options=nosniff no proxy, o MIME correto é obrigatório.
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/ttf", ".ttf")

app.include_router(auth_router.router)
app.include_router(wards_router.router)
app.include_router(beds_router.router)
app.include_router(events_router.router)
app.include_router(painel_router.router)
app.include_router(reports_router.router)
app.include_router(users_router.router)


@app.get("/healthz")
def healthz(db: DbSession = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


# Pasta frontend/ fica um nivel acima de backend/ (irmas no repositorio).
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


# Mantem URLs curtas para navegacao sem remover a compatibilidade com os
# arquivos .html. As paginas continuam sendo arquivos estaticos, mas passam
# primeiro por rotas explicitas como /login e /dashboard.
FRIENDLY_PAGES = {
    "login": "login.html",
    "dashboard": "dashboard.html",
    "leitos": "leitos.html",
    "indicadores": "indicadores.html",
    "pendencias": "pendencias.html",
    "relatorio": "relatorio.html",
    "usuarios": "usuarios.html",
    "painel": "painel.html",
    "alterar-senha": "alterar-senha.html",
}


@app.get("/", include_in_schema=False)
def application_entry():
    return RedirectResponse(url="/login", status_code=302)


@app.get("/login", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
@app.get("/leitos", include_in_schema=False)
@app.get("/indicadores", include_in_schema=False)
@app.get("/pendencias", include_in_schema=False)
@app.get("/relatorio", include_in_schema=False)
@app.get("/usuarios", include_in_schema=False)
@app.get("/painel", include_in_schema=False)
@app.get("/alterar-senha", include_in_schema=False)
def friendly_page(request: Request):
    page_name = request.url.path.removeprefix("/")
    filename = FRIENDLY_PAGES.get(page_name)
    if filename is None:
        raise HTTPException(status_code=404, detail="Pagina nao encontrada")

    page_path = FRONTEND_DIR / filename
    if not page_path.is_file():
        raise HTTPException(status_code=404, detail="Pagina nao encontrada")
    return FileResponse(page_path)


# Precisa ser o ULTIMO mount registrado: como esta em "/", ele so entra em
# acao pra qualquer caminho que nao bateu em nenhuma rota da API acima
# (login.html, index.html, registro.html, /assets/..., /img/...).
# html=True faz "/" servir automaticamente o index.html da pasta.
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend") 
   
