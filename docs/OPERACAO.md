# Implantação e operação

## Pré-requisitos

- Docker Engine com Docker Compose.
- DNS apontando para o servidor.
- Certificado e chave TLS em `deploy/certs/fullchain.pem` e
  `deploy/certs/privkey.pem`.
- Cópia de `backend/.env.production.example` como
  `backend/.env.production`, com segredos reais.
- `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` definidos no ambiente
  que executará o Compose.

Nunca salve segredos reais no Git. O arquivo `backend/.env.production` já está
ignorado pelo projeto.

### HTTP restrito à rede interna

Quando a política institucional exigir HTTP, mantenha o ambiente como produção
e autorize explicitamente essa exceção no arquivo `.env.production`:

```env
ENVIRONMENT=production
COOKIE_SECURE=false
ALLOW_INSECURE_INTERNAL_HTTP=true
```

Restrinja a porta 80 no firewall somente às redes internas autorizadas. Essa
opção não deve ser usada para uma aplicação exposta à internet.

## Transferência do Windows para a VM Linux

No Windows, na raiz do projeto:

```powershell
.\deploy\package.ps1
```

O comando cria `deploy/releases/setup-leitos-AAAAMMDD-HHMMSS.tar.gz` e mostra
seu SHA-256. O pacote não contém banco local, `.env`, senhas, certificados,
backups, testes, caches ou ambiente virtual.

Envie o arquivo usando o usuário e endereço reais da VM:

```powershell
scp .\deploy\releases\setup-leitos-AAAAMMDD-HHMMSS.tar.gz usuario@IP_DA_VM:/tmp/
```

Na VM:

```bash
sha256sum /tmp/setup-leitos-AAAAMMDD-HHMMSS.tar.gz
sudo mkdir -p /opt/setup-leitos
sudo tar -xzf /tmp/setup-leitos-AAAAMMDD-HHMMSS.tar.gz -C /opt/setup-leitos
sudo chown -R "$USER":"$USER" /opt/setup-leitos
cd /opt/setup-leitos
```

Compare o SHA-256 da VM com o exibido no Windows antes de continuar. Crie
`backend/.env.production` diretamente na VM e nunca o envie pelo `scp`.

O `backend/app.db` local é SQLite e não deve ser copiado para o PostgreSQL de
produção. Se houver dados reais que precisem ser preservados, faça uma migração
de dados separada antes da troca; não trate a cópia do arquivo como restauração.

## Validação da configuração

Antes do primeiro seed:

```powershell
cd backend
python -m scripts.verify_production --env-file .env.production --initial-seed
cd ..
```

Depois do seed, remova `SEED_COORDINATOR_PASSWORD` e
`SEED_ADMIN_PASSWORD` do arquivo e execute:

```powershell
cd backend
python -m scripts.verify_production --env-file .env.production
cd ..
```

O verificador recusa ambiente diferente de produção, SQLite, segredo de
exemplo, cookie inseguro, homologação habilitada e senhas iniciais mantidas
após o seed.

## Primeira implantação

```powershell
docker compose build
docker compose up -d db
docker compose run --rm app alembic upgrade head
docker compose run --rm app python -m scripts.seed_data
docker compose up -d
docker compose ps
```

Depois do primeiro seed, remova `SEED_COORDINATOR_PASSWORD` e
`SEED_ADMIN_PASSWORD` de `.env.production`.

## Atualização

```powershell
.\deploy\backup.ps1
docker compose build
docker compose run --rm app alembic upgrade head
docker compose up -d
docker compose ps
```

Não aumente `--workers` enquanto o painel usar o gerenciador WebSocket em
memória. Para múltiplas instâncias, migre o broadcast para Redis Pub/Sub.

## Backup

Na VM Linux:

```bash
sudo chmod 750 deploy/backup.sh deploy/restore.sh
sudo ./deploy/backup.sh
```

Os arquivos compactados e seus SHA-256 ficam em `deploy/backups`. A retenção
padrão é de 30 dias e pode ser alterada com `BACKUP_RETENTION_DAYS`. Copie os
backups para armazenamento externo ao servidor.

Para instalar o agendamento diário das 02h:

```bash
sudo install -m 644 deploy/setup-leitos-backup.service /etc/systemd/system/
sudo install -m 644 deploy/setup-leitos-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now setup-leitos-backup.timer
systemctl list-timers setup-leitos-backup.timer
```

## Restauração

Faça a restauração primeiro em homologação. Na VM Linux, a operação exige
`--yes`, valida gzip e SHA-256, para a aplicação durante a carga, reaplica as
migrações e inicia a aplicação novamente:

```bash
sudo ./deploy/restore.sh --yes \
  /opt/setup-leitos/deploy/backups/setup-leitos-AAAAMMDD-HHMMSS.sql.gz
```

Na VM, `docker-compose.override.yml` é carregado automaticamente. Ele publica
somente a aplicação em `127.0.0.1:8002` e coloca o Nginx do Docker em um perfil
desabilitado, evitando conflito com o Apache das portas 80/443.

## Monitoramento

- `GET /healthz` verifica API e banco.
- `docker compose ps` mostra saúde dos containers.
- `docker compose logs --since 30m app proxy db` consulta logs recentes.
- Monitore espaço do volume PostgreSQL, validade do certificado e falhas 429/5xx.

## Incidente

1. Preserve os logs e faça backup antes de alterações.
2. Confirme saúde do banco e do container da aplicação.
3. Se necessário, restaure o último backup validado em um ambiente separado.
4. Nunca execute o gerador de homologação em produção.
