# Infra

Infrastructure notes and deployment assets for Pàdéyá.

## Local stack

Use the root `docker-compose.yml` for PostgreSQL, Redis, backend, and frontend (development, hot-reload).

## Production

See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md).

| Asset | Path |
|-------|------|
| Production Compose | `../docker-compose.prod.yml` |
| Nginx example | `nginx/padeya.conf.example` |
| Deploy scripts | `../scripts/deploy.sh`, `prod-*.sh` |
| Env templates | `../backend/.env.production.example`, `../frontend/.env.production.example` |

## Later

- Managed Postgres and Redis
- CI/CD secrets via environment injection (never committed)
- Observability (logs, metrics, traces)
- Kubernetes manifests if needed
