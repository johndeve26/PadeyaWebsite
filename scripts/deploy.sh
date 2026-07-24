#!/usr/bin/env bash
# Deploy / update the Pàdéyá production Docker stack on a VPS.
# Safe defaults: no demo seed, requires production env files.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE=(docker compose -f docker-compose.prod.yml)
ENV_FILE="${ENV_FILE:-frontend/.env.production}"
BACKEND_ENV="${BACKEND_ENV:-backend/.env.production}"

die() { echo "ERROR: $*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "docker is required"
docker compose version >/dev/null 2>&1 || die "docker compose plugin is required"

[[ -f "$BACKEND_ENV" ]] || die "Missing $BACKEND_ENV — copy from backend/.env.production.example"
[[ -f "$ENV_FILE" ]] || die "Missing $ENV_FILE — copy from frontend/.env.production.example"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

[[ "${NEXT_PUBLIC_API_URL:-}" != *localhost* ]] || die "NEXT_PUBLIC_API_URL must not use localhost"
[[ "${NEXT_PUBLIC_DEMO_MODE:-false}" == "false" ]] || die "NEXT_PUBLIC_DEMO_MODE must be false for production deploy"
[[ -n "${POSTGRES_PASSWORD:-}" && "${POSTGRES_PASSWORD}" != "CHANGE_ME_STRONG_PASSWORD" ]] \
  || die "Set a real POSTGRES_PASSWORD in $ENV_FILE"

if [[ "${SKIP_GIT_PULL:-0}" != "1" ]]; then
  echo "==> Pulling latest code"
  git pull --ff-only
fi

echo "==> Validating compose file"
"${COMPOSE[@]}" --env-file "$ENV_FILE" config >/dev/null

echo "==> Building images"
"${COMPOSE[@]}" --env-file "$ENV_FILE" build

echo "==> Starting / recreating services"
"${COMPOSE[@]}" --env-file "$ENV_FILE" up -d --remove-orphans

echo "==> Database migrations (alembic upgrade head)"
"${COMPOSE[@]}" --env-file "$ENV_FILE" exec -T backend alembic upgrade head

echo "==> Waiting for backend health"
for i in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${BACKEND_HOST_PORT:-8000}/health" >/dev/null 2>&1; then
    echo "Backend healthy."
    break
  fi
  if [[ "$i" -eq 40 ]]; then
    die "Backend health check timed out — run: ./scripts/prod-logs.sh"
  fi
  sleep 3
done

echo "==> Frontend smoke"
curl -fsS -o /dev/null "http://127.0.0.1:${FRONTEND_HOST_PORT:-3000}/" \
  || die "Frontend did not respond on :${FRONTEND_HOST_PORT:-3000}"

echo "==> Service status"
"${COMPOSE[@]}" --env-file "$ENV_FILE" ps

echo
echo "Deploy complete."
echo "  Frontend: http://127.0.0.1:${FRONTEND_HOST_PORT:-3000}"
echo "  Backend:  http://127.0.0.1:${BACKEND_HOST_PORT:-8000}/health"
echo "Point Nginx at these ports (see infra/nginx/padeya.conf.example)."
