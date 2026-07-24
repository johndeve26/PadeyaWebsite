# Event recommendations (fan)

Rules-only personalized event discovery for signed-in fans. Does **not** replace the public `/events` marketplace filters or editorial Pàdéyá Picks.

## API

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/events/recommendations` | Fan | Ranked events (score 0–100) |
| POST | `/api/v1/events/recommendations/impressions` | Fan | Batch impression log |
| POST | `/api/v1/events/recommendations/{event_id}/feedback` | Fan | viewed/clicked/saved/purchased/dismissed/not_interested/hide_category/hide_host/more_like_this |
| GET | `/api/v1/admin/recommendations/events/debug?user_id=` | Admin | Candidate/exclusion/score breakdown |

Query: `limit`, `cursor`, `city`, `area`, `category`, `date_range`, `mode` (`recommended`, `near_you`, `similar_to_attended`, `followed_hosts`, `friends_going`, `trending`), `exclude_event_id`, `context_event_id`, `host_id` (context hints for detail/list surfaces).

Event detail (`/events/[slug]`, signed-in): **More events you may like** uses `surface=event_detail_recommended`, passes `context_event_id` + category/city from the current event, and always excludes the current event. Logged-out users keep the rules-based related block (host/city/category via `RelatedDiscoverySection`).

## Scoring (0–100)

Deterministic groups: interest (30), host (20), location (20), social (15), trust/activity (15), freshness (10). Show when score ≥ min (default 35) and at least one safe reason.

Excludes: unpublished/unlisted/password events (without access), ended/cancelled, active dismiss, hidden category/host, already purchased upcoming tickets, own-host events.

Penalties: expired dismiss, ignored impressions (≥ threshold, no click/save), category/host hide feedback.

No AI. No private spend, VIP/table, messages, vault, or fan names in reasons.

## Surfaces

- `dashboard_events_for_you`
- `events_recommended_rail` — `/events`
- `events_sort_recommended` — `/events?sort=recommended`
- `event_detail_recommended`

## Admin

Runtime category **`event-recommendations`** at `/admin/settings/runtime/event-recommendations` (alias `/admin/discovery/event-recommendations`).

## Module

`backend/app/events/recommendations/` — constants, affinity, scoring, engine, pool, service, models, settings, router, admin_router.
