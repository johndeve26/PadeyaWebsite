# Pàdéyá sponsorship production smoke validation

**Run date:** 2026-07-23  
**Environment:** Local CI-style (pytest + SQLite/Postgres test DB from `conftest.py`)  
**Payments:** Paystack **test mode only** (`initialize_transaction` mocked; webhook signed with test secret from `conftest` seed). No live charges.

**Scope:** Sponsor profile → team → saved → campaigns → recommendations → deals/invoices/webhook → deliverables → reports → admin surfaces.  
**Out of scope (confirmed):** Manual non-payment deal approval (not implemented). New sponsor features (not added in this run).

---

## 1. Migrations

| Revision | Description | Chain |
| --- | --- | --- |
| `20260723_0133` | Sponsor profile workspace | `20260722_0132` → `0133` |
| `20260723_0134` | Sponsor team invites / audit | `0133` → `0134` |
| `20260723_0135` | Sponsor saved items | `0134` → `0135` |
| `20260723_0136` | Sponsor campaigns | `0135` → `0136` |
| `20260723_0137` | Campaign recommendations | `0136` → `0137` |
| `20260723_0138` | Sponsorship deals / invoices / payment events | `0137` → `0138` |
| `20260723_0139` | Sponsorship deliverables | `0138` → `0139` |

**Alembic head:** `20260723_0139` (single linear head, verified via `alembic heads` and `alembic history`).

**Deploy action:** Apply through `0139` on production/staging before enabling sponsor deal UI.

---

## 2. Validation matrix

| Area | Automated coverage | Result | Notes |
| --- | --- | --- | --- |
| Sponsor profile / workspace | `test_sponsor_profiles.py` (8) | **Pass** | Create, slug, owner edit, public directory hides unapproved, admin verify/restrict, no fan private API |
| Sponsor team | `test_sponsor_team.py` (6) | **Pass** | Invite, accept, roles, viewer constraints, owner not removable |
| Saved items | `test_sponsor_saved.py` | **Pass** | Save targets, notes, availability |
| Campaigns | `test_sponsor_campaigns.py` | **Pass** | CRUD, saved links, inquiry `campaign_id`, moderation, private not in public API |
| Recommendations | `test_sponsor_campaign_recommendations.py` (8) | **Pass** | Scoring, dismissals, safe payloads |
| Deal lifecycle | `test_sponsorship_deals.py` (8) | **Pass** | Proposal → accept → invoice → pay init (no paid) → webhook → active placement → idempotent webhook → RBAC → admin no raw payload |
| Deliverables | `test_sponsorship_deliverables.py` (7) | **Pass** | Seed on active, submit/approve/reject, reports counts, notification on submit, full completion → deal `completed` |
| Reports | `test_sponsor_reports.py` (4) | **Pass** | Overview + campaign; no fan PII strings in body |
| Host marketplace (legacy) | `test_sponsorships.py` (8) | **Pass** | Public slots/hosts cache invalidated on publish/moderate/settings; visibility regression tests |
| Rich sponsor demo seed | `test_sponsor_demo_seed.py` (4) | **Pass** | ≥5 public sponsored events per verified brand; enriched cards; no Paystack/notify |
| Notifications (subset) | Deliverables submit test | **Pass** | In-app notification queued on deliverable submit; other kinds registered in `channel_registry` (proposal, deal active, approve/reject, all complete) — not all asserted in tests |
| Admin UI routes | Static | **Pass** | `admin/sponsors`, `admin/sponsor-campaigns`, `admin/sponsorship-deals` pages present; permission strings in page components |
| Sponsor UI routes | Static | **Pass** | `/sponsor/*` workspace + `/sponsor/deals/*` + host `/host/sponsorships/deals/*` |

---

## 3. Payment & webhook (test mode)

| Check | Result |
| --- | --- |
| Paystack init returns `payment_url` (mocked) | **Pass** (`test_pay_init_does_not_mark_paid`) |
| Frontend return URL does **not** mark paid | **Pass** (status stays `payment_pending` until webhook) |
| Verified webhook marks invoice paid + deal `active` | **Pass** |
| `SponsorshipPlacement` activated on webhook | **Pass** |
| Duplicate webhook idempotent | **Pass** |
| Reference prefix `PDY-SPN-` routed before ticket orders | **Pass** (code path in `payments/webhook.py`) |

---

## 4. Privacy

| Check | Result |
| --- | --- |
| Sponsor reports omit attendee / raw payment payload | **Pass** (explicit tests) |
| Admin deal API omits `raw_payload` | **Pass** |
| Public sponsor / private campaign budgets | **Pass** (`test_private_campaign_not_in_public_api`, directory tests) |
| Deliverables / deal notifications use safe titles only | **Pass** (by design; submit notification test checks no card secrets in body) |

---

## 5. Test run summary

**Primary sponsor workspace suite:**

```bash
cd backend && python3 -m pytest \
  tests/test_sponsor_profiles.py \
  tests/test_sponsor_team.py \
  tests/test_sponsor_saved.py \
  tests/test_sponsor_campaigns.py \
  tests/test_sponsor_campaign_recommendations.py \
  tests/test_sponsorship_deals.py \
  tests/test_sponsorship_deliverables.py \
  tests/test_sponsor_reports.py \
  -q
```

**Result:** **54 passed** (~54s).

**Full sponsor + marketplace gate (recommended CI):**

```bash
cd backend && python3 -m pytest tests/test_sponsor_*.py tests/test_sponsorship*.py -q
```

**Result:** **62 passed** (~63s).

---

## 6. Smoke verdict

| | |
| --- | --- |
| **Overall** | **PASS for sponsor workspace + marketplace deploy** |
| **Blockers** | None |
| **Warnings** | (1) Frontend sponsor vitest not in npm scripts. (2) Notification kinds beyond deliverable-submit not exhaustively asserted. (3) “Deliverable due soon” — channel registered; no scheduled job validated in this smoke. |
| **Manual non-payment approval** | Not enabled (by design) |

---

## 7. Pre-deploy checklist (ops)

1. Run Alembic through **`20260723_0139`**.
2. Confirm Paystack **test** keys in staging; **live** keys only after smoke on staging with test mode.
3. Run the **62-test** pytest command (`tests/test_sponsor_*.py tests/test_sponsorship*.py`) on the release branch.
4. Spot-check admin pages with a user holding `admin.sponsorship_deals.view` (no raw Paystack JSON in network responses).
5. Confirm `frontend_url` / callback URLs for sponsor deal payment return paths.

See also: [SPONSORSHIPS.md](./SPONSORSHIPS.md), [PRIVACY.md](./PRIVACY.md), [API.md](./API.md).
