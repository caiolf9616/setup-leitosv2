#!/usr/bin/env bash
set -Eeuo pipefail

umask 077
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
BACKUP_DIR="${PROJECT_ROOT}/deploy/backups"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
COMPOSE=(docker compose -f "${PROJECT_ROOT}/docker-compose.yml" -f "${PROJECT_ROOT}/docker-compose.override.yml")

mkdir -p -- "${BACKUP_DIR}"
BACKUP_DIR="$(cd -- "${BACKUP_DIR}" && pwd -P)"
case "${BACKUP_DIR}" in
  "${PROJECT_ROOT}"/deploy/backups) ;;
  *) echo "Diretório de backup inválido: ${BACKUP_DIR}" >&2; exit 1 ;;
esac

timestamp="$(date -u +%Y%m%d-%H%M%S)"
destination="${BACKUP_DIR}/setup-leitos-${timestamp}.sql.gz"
temporary="${destination}.partial"

cleanup() {
  rm -f -- "${temporary}"
}
trap cleanup EXIT

"${COMPOSE[@]}" exec -T db sh -c \
  'pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --clean --if-exists --no-owner' \
  | gzip -9 > "${temporary}"

test -s "${temporary}"
gzip -t "${temporary}"
mv -- "${temporary}" "${destination}"
trap - EXIT

find "${BACKUP_DIR}" -maxdepth 1 -type f \
  \( -name 'setup-leitos-*.sql.gz' -o -name 'setup-leitos-*.sql.gz.sha256' \) \
  -mtime "+${RETENTION_DAYS}" -delete

sha256sum "${destination}" > "${destination}.sha256"
echo "Backup concluído: ${destination}"
