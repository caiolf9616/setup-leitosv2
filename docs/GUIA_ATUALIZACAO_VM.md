# Guia de atualização da VM

Este procedimento publica uma nova versão do Controle de Leitos na VM
`10.10.29.90`. A aplicação em produção fica em `/opt/setup-leitos`.

## 1. Validar o projeto no Windows

Abra o PowerShell na pasta do projeto:

```powershell
cd C:\Users\caio.fernandes\Desktop\setup-de-leitos-v2
cd backend
..\.venv\Scripts\python.exe -m pytest tests -q
cd ..
```

Continue somente se todos os testes passarem.

## 2. Criar o pacote

```powershell
.\deploy\package.ps1
```

Anote o nome do arquivo e o SHA-256 exibidos. O pacote será criado em
`deploy\releases` sem senhas, banco local, certificados, ambiente virtual ou
caches.

## 3. Enviar para a VM

Substitua `NOME-DO-PACOTE.tar.gz` pelo arquivo criado:

```powershell
scp .\deploy\releases\NOME-DO-PACOTE.tar.gz caio@10.10.29.90:/tmp/
```

A transferência precisa chegar a `100%`.

## 4. Entrar na VM e fazer backup

```powershell
ssh caio@10.10.29.90
```

Já dentro da VM:

```bash
cd /opt/setup-leitos
sudo bash ./deploy/backup.sh
```

O comando deve informar `Backup concluído` e o caminho de um arquivo `.sql.gz`.
Não prossiga se o backup falhar.

## 5. Conferir o pacote

```bash
sha256sum /tmp/NOME-DO-PACOTE.tar.gz
```

Compare o resultado com o SHA-256 exibido no Windows. Os dois valores precisam
ser idênticos.

## 6. Instalar a atualização

```bash
tar -xzf /tmp/NOME-DO-PACOTE.tar.gz -C /opt/setup-leitos
chmod 750 deploy/backup.sh deploy/restore.sh
sudo docker compose build app
sudo docker compose run --rm app alembic upgrade head
sudo docker compose up -d
```

Pare no primeiro erro e não continue os comandos seguintes até entender a
causa. A reconstrução pode deixar o sistema indisponível por alguns segundos.

## 7. Confirmar que está funcionando

Aguarde aproximadamente 20 segundos:

```bash
sudo docker compose ps
curl -fsS http://127.0.0.1:8002/healthz
```

Os serviços `app` e `db` devem aparecer como `healthy`. A API deve responder:

```json
{"status":"ok","database":"ok"}
```

Depois, abra `http://10.10.29.90/login` em um computador ou celular e confira
a funcionalidade alterada. Se o navegador mostrar a versão antiga, atualize a
página ou limpe o cache do site.

## 8. Consultar erros

```bash
sudo docker compose logs --since 15m app db
```

Não copie senhas, conteúdo do `.env` ou cookies para mensagens e chamados.

## 9. Restaurar o banco em uma emergência

Use somente quando houver perda ou corrupção confirmada de dados. Identifique o
backup criado antes da atualização:

```bash
ls -lh /opt/setup-leitos/deploy/backups
```

O procedimento de restauração substitui os dados atuais. Leia primeiro
`docs/OPERACAO.md` e execute somente com o arquivo correto:

```bash
sudo bash ./deploy/restore.sh --yes /opt/setup-leitos/deploy/backups/NOME-DO-BACKUP.sql.gz
```

Nunca restaure um backup apenas para corrigir aparência ou código do frontend.
