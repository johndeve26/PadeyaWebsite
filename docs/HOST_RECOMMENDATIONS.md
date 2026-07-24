# Host recommendations (fan)

Rules-only personalized host discovery for signed-in fans. Does **not** change the public `/hosts` marketplace scoring or visibility thresholds.

## API

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/hosts/recommendations` | Fan | Ranked list (score 0–100, min show from runtime config) |
| POST | `/api/v1/hosts/recommendations/impressions` | Fan | Batch impression log (surface, position, score, reason codes) |
| POST | `/api/v1/hosts/recommendations/{host_id}/dismiss` | Fan | Hide host for dismissal cooldown |
| POST | `/api/v1/hosts/recommendations/{host_id}/not-interested` | Fan | Dismiss + category penalty |
| POST | `/api/v1/hosts/recommendations/{host_id}/more-like-this` | Fan | Boost similar categories/cities |
| POST | `/api/v1/hosts/recommendations/{host_id}/click` | Fan | Positive engagement signal |
| POST | `/api/v1/hosts/recommendations/{host_id}/follow` | Fan | Positive engagement after follow |
| POST | `/api/v1/hosts/recommendations/hide-category` | Fan | Hide category slug for configured days |
| GET | `/api/v1/admin/recommendations/hosts/debug?user_id=` | Admin | Candidate/exclusion/score breakdown |

## Surfaces (frontend)

- `dashboard_overview` — dashboard rail
- `dashboard_hosts_for_you` — `/dashboard/hosts-for-you`
- `hosts_recommended_rail` — `/hosts` “Recommended for you”
- `hosts_sort_recommended` — `/hosts?sort=recommended` (directory order)

## Scoring (summary)

Pool from `list_discover_hosts` (configurable size). Excludes: own host, already followed, active dismiss, hidden category, below min score, no safe reason.

Signals: tickets/check-ins, follows, Fan Connect peer follows, passport categories, city/nearby, verified/upcoming/trust, feedback (more-like boost, impression ignore penalty, expired dismiss penalty).

No AI ranking. No private spend, VIP/table, messages, vault, or fan names in reason labels.

## Admin tuning

Runtime category **`host-recommendations`** at `/admin/settings/runtime/host-recommendations` (alias `/admin/discovery/host-recommendations`). Changes are audit-logged via runtime settings.

## Privacy

Reason chips use fixed copy from `REASON_LABELS` in `backend/app/hosts/recommendations/constants.py`. Impression rows store only host id, surface, position, score, and reason **codes** — not message content or financial data.
