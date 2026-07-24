# Analytics rollups

Pàdéyá stores an append-only `analytics_events` stream, then aggregates it into
daily rollup tables for faster dashboards and exports.

**No Celery required.** Run the CLI on a schedule (cron / container one-shot).

## What gets recalculated

For each product event × UTC calendar day in the window:

| Table | Slice |
|---|---|
| `event_daily_analytics` | Funnel + revenue totals |
| `event_source_analytics` | UTM / source / medium / campaign |
| `event_ticket_type_analytics` | Ticket type impressions → sales |
| `event_geo_device_analytics` | Country / city / device / browser |

Recalculation is **idempotent**: existing rows are upserted. Re-running the same
window is safe and recommended (catches late webhook / trusted events).

Bots (`is_bot=true`) are excluded from rollups.

## Manual run

From `backend/`:

```bash
# Explicit month
python -m scripts.run_analytics_rollups --date-from 2026-01-01 --date-to 2026-01-31

# Rolling window (includes today, UTC)
python -m scripts.run_analytics_rollups --last-days 7

# Yesterday + today (default when no flags are passed)
python -m scripts.run_analytics_rollups

# Single product event
python -m scripts.run_analytics_rollups --last-days 30 --event-id <event-uuid>
```

Exit code `0` on success, non-zero on failure.

## Docker

With Compose (service name `backend`):

```bash
docker compose exec backend \
  python -m scripts.run_analytics_rollups --last-days 7

docker compose exec backend \
  python -m scripts.run_analytics_rollups \
  --date-from 2026-01-01 --date-to 2026-01-31
```

One-shot run without an interactive shell:

```bash
docker compose run --rm backend \
  python -m scripts.run_analytics_rollups --last-days 2
```

Production Compose (`docker-compose.prod.yml`) uses the same pattern against the
API container:

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -m scripts.run_analytics_rollups --last-days 2
```

## Cron examples

Run as the deploy user with the backend virtualenv (or Docker) on the host.

### Host cron (venv)

```cron
# Every day at 01:15 UTC — recompute last 2 days
15 1 * * * cd /opt/padeya/backend && /opt/padeya/backend/.venv/bin/python -m scripts.run_analytics_rollups --last-days 2 >> /var/log/padeya/analytics-rollups.log 2>&1

# Weekly Sunday 02:00 UTC — backfill last 14 days
0 2 * * 0 cd /opt/padeya/backend && /opt/padeya/backend/.venv/bin/python -m scripts.run_analytics_rollups --last-days 14 >> /var/log/padeya/analytics-rollups.log 2>&1
```

### Host cron (Docker)

```cron
15 1 * * * cd /opt/padeya && docker compose exec -T backend python -m scripts.run_analytics_rollups --last-days 2 >> /var/log/padeya/analytics-rollups.log 2>&1
```

Use `-T` so cron does not allocate a TTY.

## Ops notes

- Prefer `--last-days 2` nightly so late-arriving trusted commerce events land in
  yesterday’s rollup.
- After a large demo seed or data repair, run an explicit `--date-from` /
  `--date-to` backfill once.
- Code entry points: `app.analytics.rollups.run_rollups` and
  `recalculate_all_for_event_day` (also used by the demo analytics seeder).
- Dashboards may still query live SQL; rollups are the durable aggregate layer
  for scheduled refresh and future read-path optimization.
