#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${1:-}" != "--yes" || -z "${2:-}" ]]; then
  echo "Uso: $0 --yes /opt/setup-leitos/deploy/backups/arquivo.sql.gz" >&2
  exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
BACKUP_DIR="${PROJECT_ROOT}/deploy/backups"
BACKUP_FILE="$(realpath -e -- "$2")"
COMPOSE=(docker compose -f "${PROJECT_ROOT}/docker-compose.yml" -f "${PROJECT_ROOT}/docker-compose.override.yml")

case "${BACKUP_FILE}" in
  "${BACKUP_DIR}"/setup-leitos-*.sql.gz) ;;
  *) echo "O backup precisa estar em ${BACKUP_DIR}" >&2; exit 1 ;;
esac

gzip -t "${BACKUP_FILE}"
if [[ -f "${BACKUP_FILE}.sha256" ]]; then
  (cd -- "$(dirname -- "${BACKUP_FILE}")" && sha256sum -c "$(basename -- "${BACKUP_FILE}.sha256")")
fi

restart_app() {
  "${COMPOSE[@]}" up -d app
}
trap restart_app EXIT

"${COMPOSE[@]}" stop app
gzip -dc -- "${BACKUP_FILE}" |
  "${COMPOSE[@]}" exec -T db sh -c \
    'psql --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --set ON_ERROR_STOP=on'
"${COMPOSE[@]}" run --rm app alembic upgrade head

trap - EXIT
restart_app
echo "Restauração concluída: ${BACKUP_FILE}"
