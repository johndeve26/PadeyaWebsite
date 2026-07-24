# Host-as-Fan (Pàdéyá)

Hosts are still **Personal / Fan users**. Owning a host workspace does not remove Personal dashboard, Fan Passport, Fan Connect, or the ability to fan **other** hosts.

Canonical code: `backend/app/hosts/fan_self_abuse.py` · FE CTAs: `frontend/src/lib/own-host-ctas.ts`.

Related: [CHECKOUT.md](./CHECKOUT.md) · [REVIEWS.md](./REVIEWS.md) · [MESSAGING.md](./MESSAGING.md) · [AMBASSADORS.md](./AMBASSADORS.md) · [FAN_PASSPORT.md](./FAN_PASSPORT.md) · [PRIVACY.md](./PRIVACY.md) · [SECURITY.md](./SECURITY.md) · [DEMO_DATA.md](./DEMO_DATA.md)

## Who is blocked

Only the **host owner** (`hosts.user_id === current_user.id`) is blocked from Personal/Fan/customer actions against **their own** host.

| Actor | Own host (Host A) | Other host (Host B) |
|-------|-------------------|---------------------|
| Host A **owner** | Blocked (rules below) | Allowed normally |
| Host A **team / staff / scanner / merch / volunteer** | Allowed as fans when product rules allow | Allowed |
| Ambassador / promoter for Host A | Allowed as fans (commission rules separate) | Allowed |
| Ordinary fan | N/A | Allowed |

## Allowed for every host user

- Keep Personal dashboard (`/dashboard`) and Fan Passport
- Buy tickets/merch, follow, review, and message **other** hosts
- Host A owner may still fan Host B normally
- Use Host workspace tools for their own events (manage, not “buy as customer”)

## Blocked for own host (owner only)

| Action | Copy / detail constant | HTTP |
|--------|------------------------|------|
| Buy tickets / merch / checkout | `CHECKOUT_OWN_HOST_DETAIL` — “You can’t buy tickets or merch from your own host workspace.” | 403 |
| Public event / merch review | `REVIEW_OWN_HOST_DETAIL` — “You can’t publicly review your own host workspace.” | 403 |
| Fan→host messaging from Personal | `MESSAGING_OWN_HOST_DETAIL` — “You can’t message your own host workspace from your Personal account.” | 403 |
| Follow own host (+ marketing opt-in) | `FOLLOW_OWN_HOST_DETAIL` — “You can’t follow your own host profile.” | 400 |
| Join own ambassador campaign for reward* | Host-owner commission guard | — |
| Earn commission on own host campaign* | Host-owner commission guard | — |
| Self-referral (buyer == ambassador) | Always blocked for any actor | — |

\*Unless `ambassador_campaigns.allow_host_owner_commission` is explicitly true.

Also kept (any actor): Fan Connect to self · Vault subscribe to own host · invite self to host team · transfer ticket to self.

## Public UI (owner)

| Surface | Own-host CTA | Hidden |
|---------|--------------|--------|
| Host Legacy / profile | Banner “This is your host page” · **Open Host workspace** | Follow · Message · Connect |
| Own event page | **Manage event** | Buy ticket · Buy merch checkout |

Team/staff viewing the same public pages are treated as **visitors** for these CTAs (they may still buy/follow when allowed).

## Metrics & trust

Owner self-actions must not inflate public popularity, Legacy ranking, follower counts, or review aggregates. Collectors exclude owner tickets / reviews / followers where applicable.

## Test / admin / demo — do not inflate metrics

- **No production bypass** on ownership asserts (no admin / impersonation / env flag override on normal checkout paths).
- **Admin impersonation** uses the target identity; own-host owner rules still apply. Sensitive money paths are also blocked by impersonation guards.
- **Demo / seed** accounts buy and fan **other** hosts normally. Do **not** use live Paystack for owner own-host tests.
- A dedicated **local test-order helper** (if added later) must be explicit (`is_test_order` / `exclude_from_public_metrics`) and ignored by public metrics via `order_excluded_from_public_metrics`. That helper is **not** implemented in product checkout today.

## Tests

`backend/tests/test_host_as_fan.py` · Vitest `own-host-ctas.test.ts` · `host-affiliation.test.ts`.
