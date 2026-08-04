# Legacy Score

Authoritative formula and public/host presentation rules for Pàdéyá Host Legacy.

Related: [LEGACY_PAGE.md](./LEGACY_PAGE.md) (Content Studio / public page structure).

## What Legacy Score is

Legacy Score is a **0–100 weighted composite** from verified host activity. It is **not**:

- a five-star rating (that remains **Verified rating**)
- a public leaderboard or percentile
- a guarantee of safety, quality, refunds, or future performance
- editable by hosts

Legacy Tier is the highest configured tier where **score ≥ min_score** and **all hard gates** pass.

## Factor weights

Must sum to `1.00` (`backend/app/legacy/constants.py`):

| Factor key | Public label | Weight |
| --- | --- | --- |
| `verified_rating` | Verified rating / Guest satisfaction | 30% |
| `completed_events` | Completed events | 15% |
| `tickets_sold` | Tickets sold | 15% |
| `verified_checkins` | Verified check-ins | 15% |
| `refund_dispute_rate` | Refund and dispute record | 10% |
| `consistency` | Consistency | 10% |
| `repeat_buyers_followers` | Followers and repeat buyers / Community loyalty | 5% |

## Normalization

Each factor is normalized to 0–100 before weighting (`backend/app/legacy/scoring.py`).

| Factor | Rule |
| --- | --- |
| Verified rating | `(avg / 5) × 100` when `review_count > 0`, else `0` |
| Completed events | `count / 20 × 100`, cap 100 |
| Tickets sold | `count / 5000 × 100`, cap 100 |
| Verified check-ins | `count / 3000 × 100`, cap 100 |
| Refund/dispute | `100 − rate%`; **default 80** when rate is unknown |
| Consistency | 50% check-in rate + 50% completion rate |
| Followers + repeat | 50% followers/`2000` + 50% repeat-buyer % (repeat part `0` when unknown) |

Composite = Σ(factor × weight), stored to **two decimal places**.

## Caps

`SCORE_CAPS`: completed_events `20`, tickets_sold `5000`, verified_checkins `3000`, followers `2000`.

Activity above a cap still has product value; only that factor is capped for scoring.

## Hard gates

Tier selection uses configured `legacy_tiers.requirements` (not hardcoded UI defaults):

- `min_completed_events`
- `min_tickets_sold`
- `min_verified_checkins`
- `min_review_count`
- `min_average_rating`

Default catalog (seed): New Host (0) → Rising (20) → Established (40) → Certified (55) → Icon (70) → Legend (85).

## Owner self-action exclusion

Host **owner** tickets, reviews, and self-follows are excluded from Legacy metrics collectors. Team members may still count. See `app/hosts/fan_self_abuse.py`.

## Provisional policy

Backend-authoritative (`app/legacy/presentation.py`):

- fewer than **3** completed events, **or**
- fewer than **5** verified reviews

Provisional does **not** change the composite formula or tier selection. It is a presentation flag (`is_provisional`, `provisional_reasons`).

## Public display rules

| Field | Rule |
| --- | --- |
| Public score | Whole number via `display_score` (nearest, clamped 0–100) |
| Exact score | `composite_score` / `score` kept for host/admin |
| Evidence | Safe counts only; skip zero-noise rows |
| Factor bands | Grouped labels (Excellent / Strong / Good / Growing / Building history) |
| Refund unknown | Public band shows “Building history”; do not advertise the 80 placeholder |
| Next tier | Includes score remaining **and** hard gates; score-met/gate-blocked has dedicated copy |
| Top tier | No fake next tier |
| Recalc on GET | **No** — public assembly uses `rescore=False` |

Followers on the public Legacy page may be **live**; the follower contribution inside the stored composite updates on refresh/sync paths.

## Recalculation triggers

Preserve existing triggers (`refresh_host_legacy_score`):

- Host tier progress view
- Event completion
- Review create/update/moderation
- Admin recalculate host / all
- Bootstrap when score row missing

Do **not** full-rescore on every public profile view.

Admin recalculate requires `legacy.manage` or `admin.full_access` and writes audit logs.

## API surfaces

| Audience | Endpoint | Presentation |
| --- | --- | --- |
| Public | `GET /u/{username}/legacy` | `legacy_trust` summary |
| Host | `GET /legacy/me/tier` | factors, contributions, next_tier_summary, provisional |
| Admin | `GET /legacy/admin/hosts` | exact score, display_score, provisional, updated_at |
| Discover | `GET /legacy/discover/hosts` | `display_score`, `is_provisional` (no ranking by score) |

Public must not expose private dispute cases, buyer identities, fraud flags, or moderation notes.

## Frontend

- Public summary: `LegacyTrustSummaryCard`
- Transparency: `/legacy`
- Host dashboard: `/host/legacy/tier`
- Admin: `/admin/legacy`
- Frontend **never** recomputes the weighted composite

## Cache

- FE public Legacy ISR / loader revalidate ~120s
- Discover Redis TTL ~180s
- After authoritative recalc, invalidate public host caches as existing patterns allow

## Editing tiers safely

1. Change thresholds only via admin tier PATCH (`/admin/legacy/tiers`).
2. Recalculate affected hosts (or recalculate-all).
3. Confirm one Alembic head if schema changed (presentation phase needs no migration).
4. Smoke New Host, provisional, score-met/gate-blocked, and top-tier hosts.
