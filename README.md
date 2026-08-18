# Setup de Leitos v2

Aplicação web para gestão de status de leitos em tempo real, com backend em FastAPI e frontend estático em HTML/CSS/JS. O sistema permite:

- autenticação por unidade/coordenador;
- registro de eventos de leitos (alta, desocupado, apto, ocupado);
- visualização de leitos por enfermaria;
- painel público de chamada com atualização em tempo real via WebSocket;
- histórico de eventos e estado atual de cada leito.

## Visão geral

O projeto está dividido em dois blocos:

- Backend: API REST + WebSocket em FastAPI, com SQLAlchemy e PostgreSQL.
- Frontend: páginas estáticas servidas pelo próprio FastAPI.

## Estrutura do projeto

```text
backend/
  app/
    auth.py
    crud.py
    database.py
    dependencies.py
    main.py
    models.py
    routers/
      auth.py
      beds.py
      events.py
      painel.py
      wards.py
    schemas.py
    settings.py
    websocket_manager.py
  scripts/
    seed_data.py
  requirements.txt

frontend/
  assets/
    css/
    js/
  components/
  *.html
```

## Requisitos

- Python 3.10+
- PostgreSQL rodando localmente
- Dependências do arquivo [backend/requirements.txt](backend/requirements.txt)

## Configuração do ambiente

1. Crie e ative um ambiente virtual:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Crie um arquivo `.env` dentro de `backend/` com as variáveis abaixo:

```env
DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/nome_do_banco
SECRET_KEY=sua-chave-secreta
SESSION_MAX_AGE_DAYS=30
ENVIRONMENT=development
COOKIE_SECURE=false
LOGIN_MAX_ATTEMPTS=5
LOGIN_WINDOW_SECONDS=300
SEED_COORDINATOR_PASSWORD=defina-uma-senha-forte
SEED_ADMIN_PASSWORD=defina-outra-senha-forte
```

> A aplicação usa `pydantic-settings`, então o arquivo `.env` é carregado automaticamente.
> Em produção, use `ENVIRONMENT=production`, uma `SECRET_KEY` aleatória com
> pelo menos 32 caracteres e `COOKIE_SECURE=true`.

## Inicialização

### Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

A API ficará disponível em:

- http://localhost:8000
- http://localhost:8000/login para entrar no sistema
- http://localhost:8000/painel para o painel público
- http://localhost:8000/docs para a documentação Swagger

### Frontend

O frontend é servido diretamente pelo FastAPI a partir da pasta `frontend/`, então não é necessário um servidor separado.

## Migrações e seed inicial

Em um banco novo, crie ou atualize o schema com Alembic:

```bash
cd backend
python -m alembic upgrade head
```

Depois, sincronize as 11 unidades, 87 enfermarias e 307 leitos reais do
catálogo:

```bash
python -m scripts.seed_data
```

Para um banco existente que já possua exatamente o schema atual e tenha sido
criado antes da adoção do Alembic, registre a migração-base uma única vez, sem
recriar as tabelas:

```bash
python -m alembic stamp head
```

Depois desse registro inicial, use sempre `python -m alembic upgrade head`
antes de executar o seed.

## Testes automatizados

Instale as dependências de desenvolvimento e execute a suíte a partir da pasta
`backend/`:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Os testes usam um banco SQLite isolado em memória e não alteram o banco local
configurado no arquivo `.env`.

## Homologação

O projeto possui um gerador determinístico de eventos e um verificador para
uma base descartável de homologação:

```bash
python -m scripts.seed_homologation
python -m scripts.verify_homologation
```

O gerador exige `ENVIRONMENT=test` e `ALLOW_HOMOLOGATION_DATA=true`, e
não aceita uma base que já possua eventos. O roteiro manual completo está em
[docs/HOMOLOGACAO.md](docs/HOMOLOGACAO.md).

## Produção

O projeto inclui imagem Docker, PostgreSQL, proxy Nginx com HTTPS, health
checks e rotinas PowerShell de backup e restauração. Consulte
[docs/OPERACAO.md](docs/OPERACAO.md) antes da primeira implantação.

O catálogo fica em `backend/app/bed_catalog.py`. Cada enfermaria possui um
identificador técnico único (por exemplo, `D-01`) e um nome real para exibição
(`01`). Assim, números repetidos em unidades diferentes não colidem no banco
nem no painel.

O seed cria as contas iniciais `COORDENACAO` e `ADMINISTRADOR` somente quando
elas ainda não existem. As senhas vêm de `SEED_COORDINATOR_PASSWORD` e
`SEED_ADMIN_PASSWORD`; elas não ficam gravadas no código nem são exibidas no
terminal. As demais contas devem ser criadas pela tela de usuários.

## Fluxo principal do sistema

### Autenticação

- O login é feito via endpoint `/api/auth/login`.
- A sessão é mantida por cookie HTTP-only.
- O frontend usa `/api/auth/me` para validar a sessão.

### Cadastro de eventos

- O registro de eventos é feito em `/api/events`.
- Cada evento altera o status de um leito.
- O painel de chamada é atualizado em tempo real após cada novo evento.

### Painel público

- O painel lê o estado inicial via `GET /api/painel/status`.
- Em seguida, mantém conexão por WebSocket em `/ws/painel`.
- Apto, Desocupado e Alta permanecem na lista lateral.
- Mudanças nesses três estados geram chamada e voz; Ocupado e Bloqueado removem
  o leito silenciosamente.
- A carga inicial cria apenas a linha de base, portanto atualizar a TV não
  repete chamadas antigas.
- O contrato detalhado está em [docs/PAINEL.md](docs/PAINEL.md).

## Principais componentes

### Backend

- `app/main.py`: ponto de entrada da aplicação e montagem de rotas.
- `app/models.py`: modelos SQLAlchemy para enfermarias, leitos, eventos, credenciais e sessões.
- `app/routers/*`: endpoints da API para autenticação, leitos, eventos e painel.
- `app/crud.py`: operações reutilizáveis de leitura e gravação no banco.
- `app/auth.py`: autenticação por senha e criação de sessões.
- `app/websocket_manager.py`: gerenciamento das conexões do painel público.

### Frontend

- `frontend/login.html`: tela de login.
- `frontend/dashboard.html`: painel interno de navegação/visualização.
- `frontend/painel.html`: painel público de chamada.
- `frontend/assets/js/painel_display.js`: lógica de atualização em tempo real do painel.

## Observações importantes

- O projeto usa autenticação baseada em sessão e cookie, não JWT.
- O painel público não exige login.
- O backend serve o frontend diretamente, então o ambiente de desenvolvimento é relativamente simples.
- A sincronização preserva o histórico: leitos antigos com eventos são
  bloqueados em vez de apagados.
- As senhas de seed são apenas para ambiente local e não devem ser usadas em produção.

## Próximos passos sugeridos

- adicionar testes automatizados para autenticação, permissões, eventos e relatórios;
- adicionar migrações com Alembic para controle mais robusto do schema;
- preparar configurações seguras e infraestrutura para implantação em produção.
