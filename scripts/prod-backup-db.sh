#!/usr/bin/env bash
# Create a timestamped PostgreSQL dump from the production compose stack.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE=(docker compose -f docker-compose.prod.yml)
ENV_FILE="${ENV_FILE:-frontend/.env.production}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_FILE="$BACKUP_DIR/padeya-postgres-$STAMP.sql.gz"

[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 1; }

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

POSTGRES_USER="${POSTGRES_USER:-padeya}"
POSTGRES_DB="${POSTGRES_DB:-padeya}"

mkdir -p "$BACKUP_DIR"

echo "==> Dumping ${POSTGRES_DB} → ${OUT_FILE}"
"${COMPOSE[@]}" --env-file "$ENV_FILE" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
  | gzip -c > "$OUT_FILE"

ls -lh "$OUT_FILE"
echo "Backup complete. Keep this file off the app server when possible."
echo
echo "Restore example (destructive):"
echo "  gunzip -c $OUT_FILE | docker compose -f docker-compose.prod.yml --env-file $ENV_FILE exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB"
