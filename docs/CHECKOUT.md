# Checkout (Pàdéyá)

Ticket and merch checkout share the platform `orders` / `payments` stack. Money truth is server-side: verified Paystack webhook / finalize only — never trust the browser success page.

Related: [PAYMENTS.md](./PAYMENTS.md) · [TICKETS.md](./TICKETS.md) · [MERCH.md](./MERCH.md) · [COMMERCE.md](./COMMERCE.md) · [AMBASSADORS.md](./AMBASSADORS.md) · [HOST_AS_FAN.md](./HOST_AS_FAN.md)

## Core rules

- Create pending order → initialize Paystack → issue tickets / commit merch **only after** verified payment finalize (idempotent).
- Frontend success pages never create commission, inventory commit, or Passport badges.
- Promo / ambassador attribution attaches on pending checkout; commission finalizes only on paid webhook.

## Purchase modes (buyer ≠ attendee)

Checkout supports:

- **Buy for myself** — attendee prefilled from the logged-in buyer (editable).
- **Buy for someone else** — recipient name/email/(optional) phone, gift message, `send_ticket_to_recipient`, `keep_buyer_copy`.
- **Buy for a group** — per-ticket attendees, or “use same details for all”.
- **Guest checkout** — no login required before Paystack; `buyer_user_id` nullable; guest buyer name/email required; claim via hashed magic link after verified payment. Matching an existing account by email never auto-logs-in. Own-host / restricted accounts cannot bypass by checking out as guest with the same email.

Order always belongs to the **buyer**. Tickets are assigned to **attendees** (`order_attendees` → `tickets.holder_*` at issuance). Delivery emails go to buyer and/or recipient based on toggles — **only after** verified payment / free server confirm. `recipient_user_id` is never set from email alone.

Guest merch/bundles require login (tickets-only for guests in v1).

## Own-host checkout (Host-as-Fan)

Hosts remain Personal/Fan users and may checkout on **other** hosts normally.

The **host owner** cannot buy tickets or merch from **their own** host workspace:

- Guard: `assert_owner_not_buying_own_host` (`app/hosts/fan_self_abuse.py`)
- Detail: “You can’t buy tickets or merch from your own host workspace.”
- Status: **403**
- Public own-event UI hides Buy ticket / Buy merch and shows **Manage event** instead

**Not blocked:** host team, staff, scanners, merch desk, volunteers, ambassadors, and other fans buying that host’s events.

## Ambassador / referral at checkout

- Explicit checkout ambassador/promo code wins over cookie/link attribution.
- **Self-referral** (buyer user == ambassador user) remains blocked on attach + finalize (+ approve re-check).
- Host-owner commission on own campaigns blocked unless `allow_host_owner_commission` is true — see [AMBASSADORS.md](./AMBASSADORS.md#fraud-controls-phase-14).

## Test / admin flows must not inflate metrics

- No production bypass of own-host checkout.
- Impersonation does not unlock owner own-host purchases.
- Do not use live Paystack for owner own-host QA.
- Future local test orders must set `is_test_order` / `exclude_from_public_metrics` and be ignored by Legacy / discover / trust collectors (`order_excluded_from_public_metrics`).

Details: [HOST_AS_FAN.md](./HOST_AS_FAN.md).
