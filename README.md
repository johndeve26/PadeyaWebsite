# Pàdéyá

Event discovery, ticketing, host reputation, verified reviews, fan loyalty, and creator monetization.

This repository is a Next.js + FastAPI platform (Phases 1–18): auth/RBAC, hosts & events, payments & tickets, QR check-in, Legacy Pages & tiers, promos & ambassadors, host CRM, refunds & payouts, Vault, Fan Passport, Event Memories, analytics, AI Copilot, sponsorship marketplace, advanced ticketing, and PWA improvements.

## Structure

```
backend/          FastAPI + SQLAlchemy + Alembic
frontend/         Next.js App Router + Tailwind + brand UI
docs/             Architecture and product docs
infra/            Deployment notes
.cursor/rules/    Agent / engineering rules
docker-compose.yml
```

## Brand

- Official logos: `frontend/public/brand/padeya-logo-dark.png` and `padeya-logo-light.png`
- Tokens: `frontend/src/lib/brand.ts` and `frontend/src/styles/globals.css`
- Font: Manrope
- Accent: Brand Green `#8EF012` on black/white foundations
- User-facing name: **Pàdéyá** (code/domain may still use `padeya`)

## Quick start (local, without Docker)

### 1. Database

Start Postgres (and Redis) locally, or use Docker Compose for infra only.

Default URL:

```text
postgresql+psycopg2://padeya:padeya@localhost:5432/padeya
```

Create the database if needed (`createdb padeya` / Docker volume).

### 2. Backend — migrate & run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
PYTHONPATH=. python scripts/seed_rbac.py   # also runs on API startup
uvicorn app.main:app --reload --port 8000
```

Health check: [http://localhost:8000/health](http://localhost:8000/health)

### 3. Seed demo data (local only)

```bash
cd backend
source .venv/bin/activate
# Ensure DEMO_MODE=true and APP_ENV=development in .env
python -m scripts.seed_demo_data
# or wipe demo rows and reseed:
python -m scripts.seed_demo_data --reset
# clear demo rows only:
python -m scripts.reset_demo_data
```

Demo seed is **idempotent**, scoped to `@demo.padeye.test` users / `demo-*` events / known host slugs, and **refuses to run when `APP_ENV=production`**. Details: [docs/DEMO_DATA.md](docs/DEMO_DATA.md) · [backend/app/demo/README.md](backend/app/demo/README.md).

### 4. Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

App: [http://localhost:3000](http://localhost:3000)  
Demo hub (when `NEXT_PUBLIC_DEMO_MODE=true` or development): [http://localhost:3000/demo](http://localhost:3000/demo)

### Docker Compose (development)

```bash
docker compose up --build
```

Services: frontend `:3000`, backend `:8000`, postgres `:5432`, redis `:6379`.

### Production deploy

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for `docker-compose.prod.yml`, env templates, Nginx, TLS, backups, and VPS steps.

```bash
cp backend/.env.production.example backend/.env.production
cp frontend/.env.production.example frontend/.env.production
# fill secrets — never commit *.env.production
./scripts/deploy.sh
```

Post-deploy checklist: [docs/PRODUCTION_SMOKE_TEST.md](docs/PRODUCTION_SMOKE_TEST.md).

## Demo accounts

Password for all: `DemoPass123!`

| Email | Name | Role |
|-------|------|------|
| buyer@demo.padeye.test | Demo Buyer | buyer |
| host@demo.padeye.test | DJ Maze | host |
| host2@demo.padeye.test | Lagos Comedy Hub | host |
| mainland@demo.padeye.test | Mainland Vibes | host |
| tech@demo.padeye.test | Tech Connect Africa | host |
| praise@demo.padeye.test | Praise Experience | host |
| staff@demo.padeye.test | Gate Staff | host_staff |
| support@demo.padeye.test | Demo Support Agent | support_agent |
| finance@demo.padeye.test | Finance Admin | finance_admin |
| admin@demo.padeye.test | Demo Super Admin | super_admin |
| fan1@demo.padeye.test | Tolu Nightlife Explorer (@toluwave) | buyer |
| fan2@demo.padeye.test | Amaka Concert Lover (@amakaconcerts) | buyer |
| fan3@demo.padeye.test | Chidi Tech Regular (@chiditech) | buyer |
| fan4@demo.padeye.test | Sade Comedy Fan (@sadecomedy) | buyer |
| fan5@demo.padeye.test | Kunle VIP Regular (@kunlevip) | buyer |
| fan6@demo.padeye.test | Mira Lagos Explorer (@miralagos) | buyer |
| fan7@demo.padeye.test | Ada First Timer (@adafirsttimer) | buyer |
| fan8@demo.padeye.test | Bayo Campus Fan (@bayocampus) | buyer |

Demo emails are for local login only — never shown on public Fan Passports or Legacy pages.

### Manual test flows

1. **Buyer** — `/login` as buyer → `/events` → open `demo-afrobeats-night-live` → checkout → `/dashboard/tickets` → `/dashboard/passport`
2. **Check-in** — staff login → host check-in for a completed event (e.g. Detty Friday) → scan ticket public codes
3. **Host** — `host@demo.padeye.test` → `/host` events, Legacy, Vault, promos, audience, payouts
4. **Legacy** — `/@djmaze` public page + Vault
5. **Support / Finance / Admin** — refunds, payouts (paid needs Super Admin + evidence), reviews moderation, analytics
6. **Sponsors** — `/sponsors` marketplace listings

Local assets live under `frontend/public/demo/` (SVG placeholders, no external image URLs).

## Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

```bash
cd frontend
npm run lint
npm run build
npm run test:pwa
```

## Docs

Start with [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), and [docs/ROADMAP.md](docs/ROADMAP.md).

## Auth notes

Frontend login/register use `NEXT_PUBLIC_API_URL` (see `frontend/.env.example`).
Email provider defaults to `log` (no real email/SMS in local demo).
Paystack keys can stay blank locally; demo seed finalizes payments without live charges.
