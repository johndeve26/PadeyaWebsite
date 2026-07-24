#!/usr/bin/env bash
# Tail production backend + frontend logs.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE=(docker compose -f docker-compose.prod.yml)
ENV_FILE="${ENV_FILE:-frontend/.env.production}"
SERVICES="${SERVICES:-backend frontend email_worker}"

[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 1; }

# shellcheck disable=SC2086
exec "${COMPOSE[@]}" --env-file "$ENV_FILE" logs -f --tail="${TAIL:-200}" $SERVICES
