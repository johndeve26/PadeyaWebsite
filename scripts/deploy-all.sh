#!/usr/bin/env bash
# Full production deploy: optional backup, build, up, migrations, health, workers.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${ENV_FILE:-frontend/.env.production}"
COMPOSE=(docker compose -f docker-compose.prod.yml)

if [[ "${RUN_BACKUP:-1}" == "1" && -f "$ENV_FILE" ]]; then
  echo "==> Pre-deploy database backup"
  ./scripts/prod-backup-db.sh || {
    echo "WARN: backup failed — set RUN_BACKUP=0 to skip" >&2
    exit 1
  }
fi

echo "==> Deploy stack (build + up + migrate + health)"
./scripts/deploy.sh

echo "==> Worker status"
"${COMPOSE[@]}" --env-file "$ENV_FILE" ps email_worker push_worker

echo "==> Alembic revision (inside backend)"
"${COMPOSE[@]}" --env-file "$ENV_FILE" exec -T backend alembic current

echo
echo "All-in-one deploy finished. Run ./scripts/prod_preflight.py when ready for traffic."
