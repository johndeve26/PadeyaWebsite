# Tickets & check-in

Brand: **Pàdéyá**. Payments invariant: tickets issue only after **verified Paystack webhook** — [PAYMENTS.md](./PAYMENTS.md).

Related: [TEAMS.md](./TEAMS.md) · [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md) · [SECURITY.md](./SECURITY.md#check-in-phase-5) · [API.md](./API.md) · [AMBASSADORS.md](./AMBASSADORS.md) · [PROMO_CODES.md](./PROMO_CODES.md)

## Lifecycle (summary)

1. Buyer checks out → Paystack charge  
2. Webhook finalize → create `tickets` + signed QR (`typ=padeya.ticket.qr`)  
3. Buyer shows QR / public code at the door  
4. Desk validates signature, event binding, `jti` hash, status  
5. Check-in recorded; duplicate scans rejected  

Advanced: transfers (jti rotation), rotating QR, offline sync, password-gated cancel — [SECURITY.md](./SECURITY.md#advanced-ticketing-phase-17).

## Host team & desk scan

Ticket desk authorization is **hybrid** (owner · host team · event staff). See [TEAMS.md](./TEAMS.md#hybrid-scan-authorization).

| Allow when | Notes |
|---|---|
| Host owner | Full |
| Active team + `tickets.scan_qr` / `tickets.check_in` + host-wide scope | All host events |
| Active team + same perms + event in `scoped_event_ids` | Assigned events only |
| Active `event_staff_assignments` (`ticket_scanner` / `event_ops`, not expired) | Per-event desk |

**Deny:** suspended/removed team member · missing scan permission · scoped to another event · other host · inactive/expired staff.

### Privacy at the door

Scanner APIs return **minimal** data:

- Holder name  
- Public code  
- Ticket type name  
- Status / checked-in time  

**Not** returned: holder email, phone, payment refs, order secrets.

Search (`GET /checkins/events/{id}/search`) matches **name or public code** only → `DeskAttendeePublic`.

### Audit

Every validate/scan attempt can write `desk_scan_audit_logs` (`tickets.scan`, result `success` / `denied`, denial reason). Merged into host team audit feed.

### Frontend

| Path | Who |
|---|---|
| `/host/desk` | Team members with scan perms |
| `/host/events/[id]/check-in` | Owner / staff for that event |
| `/staff/check-in/[eventId]` | Assigned staff |
| Offline check-in | PWA queue → authenticated sync |

Nav shows **Scanner** (or Desk) only when `canScanTickets` for the active workspace.

## Permissions (team toggles)

| Key | Desk meaning |
|---|---|
| `tickets.scan_qr` | Scan signed QR |
| `tickets.check_in` | Complete check-in |
| `tickets.view` | View ticket context (not full buyer CRM) |
| `tickets.export_attendees` | Export (owner/admin paths — not desk-minimal) |

### Admin event buyers / attendees / exports

Platform ops (not hosts). Requires **both** `admin.events.view` and `admin.events.export_buyers`.  
`super_admin` (`admin.full_access`) satisfies all checks. Role seeds: support gets view + export + private contact; finance_admin gets view + export + finance sales.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/admin/events/{event_id}/buyers` | Filtered JSON list (paginated; private contact omitted) |
| GET | `/api/v1/admin/events/{event_id}/buyers/export` | CSV/JSON download (`format`, `mode`, filters, `reason`) |
| GET | `/api/v1/admin/events/{event_id}/buyers/exports` | Export audit history |

**Modes (`mode`):**

| Mode | Contents | Extra gate |
|---|---|---|
| `public_summary` | Public profile + ticket status + safe codes | — |
| `operations` (default) | Public + ops (seat/table, promo/ambassador, amounts lite) | Private email/phone only with `admin.events.export_private_contact` + reason |
| `finance` | Ops + full `order_id` / `ticket_id` + finance columns | `admin.finance.export_event_sales` + reason |

**Filters (list + export):** ticket type, purchase/ticket status, payment status, refund status, checked-in, purchased date range, promo code, ambassador code, search (public username / display name / safe ticket code).

**Filename:** `padeya-event-buyers-{event_slug}-{YYYYMMDD}.csv` (CSV cells sanitized against formula injection; streamed).

**Audit actions:** `admin_event_buyers_exported` · `admin_event_buyers_private_contact_exported` · `admin_event_buyers_finance_exported` (details include admin_user_id, event_id, host_profile_id, export_mode, format, filters_json, row_count, reason, ip, user_agent).

UI: `/admin/events/[id]/buyers` · `/attendees` · `/exports` (export modal: format, mode, filters summary, reason, confirm).

Legacy alias: `GET /api/v1/tickets/admin/events/{event_id}/buyers/export.csv` (operations mode).

**Never includes:** QR payloads / signed tokens / jti, Paystack or payment provider references/raw payloads, passwords, Fan Connect graph, private messages, vault secrets, private street addresses, or hidden venue details.

Catalog: [ROLES_AND_PERMISSIONS.md](./ROLES_AND_PERMISSIONS.md) · host desk export remains separate ([HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md)).

## Key tables

| Table | Purpose |
|---|---|
| `tickets` | Issued tickets + holder fields |
| `ticket_qr_tokens` | `jti_hash`, signed payload, revoke |
| `check_ins` | Scan outcomes |
| `scanner_sessions` | Desk sessions |
| `event_staff_assignments` | Per-event door staff |
| `desk_scan_audit_logs` | Scan audit |

[DATABASE.md](./DATABASE.md).

## Ambassadors (ticket attribution)

Ticket issue is unchanged: only after verified Paystack webhook. Ambassadors may **attribute** a paid ticket order to a promoter — they never issue tickets themselves.

| Checkout field | Meaning |
|---|---|
| `promo_code` | Buyer ticket discount — [PROMO_CODES.md](./PROMO_CODES.md) |
| `referral_code` | Ambassador attribution — [AMBASSADORS.md](./AMBASSADORS.md) |

Commission for `event_tickets` / `applies_to` ticket lines is created only inside payment finalize; refunds / ticket cancel reverse it. Ambassadors never see holder email, QR, or payment refs.
