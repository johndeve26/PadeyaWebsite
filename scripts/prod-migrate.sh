#!/usr/bin/env bash
# Run Alembic migrations inside the production backend container.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE=(docker compose -f docker-compose.prod.yml)
ENV_FILE="${ENV_FILE:-frontend/.env.production}"

[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 1; }

echo "==> alembic upgrade head (padeya-prod-backend)"
"${COMPOSE[@]}" --env-file "$ENV_FILE" exec -T backend alembic upgrade head
echo "Migrations complete."
