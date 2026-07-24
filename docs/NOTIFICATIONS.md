# Pàdéyá notifications

Brand: **Pàdéyá**. Never put private chat bodies, payment secrets, or Vault content in push/in-app copy.

**Admin user impersonation does not notify the target** — no email, in-app, or push. Impersonation is internal support/QA and is audited separately ([AUTH.md](./AUTH.md#admin-user-impersonation)).

Deep dive (VAPID, outbox, worker, privacy layers, test push): [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md).  
Email channel: [EMAILS.md](./EMAILS.md). Ops: [OPERATIONS.md](./OPERATIONS.md). Lifecycle: [CRUD_MATRIX.md](./CRUD_MATRIX.md).

## Delivery channels

### A. In-app popup notifications

Shown **while the user is actively using** the website (toast/popup).

- Primary: WebSocket `notification.created` on the messaging user channel
- Fallback: poll `/notifications/popup` (faster when WS offline)
- Marks `popup_shown_at` after display so the same alert does not spam
- Max 3 toasts; desktop top-right, mobile bottom; auto-dismiss ~5.5s; **View** action
- Safe toast titles (Ticket ready / New message / Merch pickup ready / …) — no private bodies
- Skips live chat noise on `/messages` pages
- History: header bell → `/dashboard/notifications`

Examples: “Ticket ready” · “New message” · “Merch pickup ready” · “Fan Connect request” · “Sponsor inquiry received”

Inbox: `/dashboard/notifications` (category filters, mark read / mark all read, click opens `link_path`) · header bell + sidebar **Alerts** badge · mobile bottom-nav Alerts. Works with browser push off.

Preferences + device push controls: `/dashboard/settings/notifications`.

Frontend registration flow:

1. User logs in — **no** browser permission prompt on first load
2. Calm prompt + `PushSettingsPanel` on notification settings
3. User clicks **Enable notifications** → browser prompt (`usePushNotifications`)
4. Service worker subscription saved; disable / remove devices from the same panel
5. In-app toasts via `NotificationToastProvider` + `NotificationPopupBridge`

### B. Browser push notifications

Shown through the **browser/device** after the user grants permission (desktop + mobile PWA where supported).

- **Opt-in only** — enable on a device + browser permission + category prefs
- Admin: `/admin/push/settings` (alias `/admin/settings/push`)
- Master + category prefs gate delivery (`push_enabled` defaults **on**; device subscription still required)
- Service worker (`public/sw.js`, cache `padeya-pwa-v24`) handles `push` + `notificationclick`
- Wire whitelist: `title`, `body`, `action_url`, `notification_id`, `tag`, `timestamp`, `icon`, `badge`
- Click focuses an existing Pàdéyá tab (or opens one) at `action_url`; fallback `/dashboard/notifications`
- Never includes: hidden venues, private locations, payment/order refs, full pickup/entry codes, shipping addresses, phone/email, chat bodies, attachment URLs, Vault content, Fan Connect graphs, or attendee lists
- Messaging default: “You have a new message on Pàdéyá.” Optional `push_message_previews`: “Name sent you a message.” (never full message text)
- Message and Fan Connect push categories default **on** (same as other categories); delivery still requires device subscription and away-only rules for messages
- Unsupported browsers: in-app channel still works; settings show a clear “not supported” state

APIs: `GET /push/vapid-public-key`, `GET/POST/DELETE /push/subscriptions`, `GET/PATCH /push/preferences` — full tables in [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md) and [API.md](./API.md).

### Push subscriptions (devices)

Table `push_subscriptions` — one user, many devices (unique `endpoint`).

| Field | Notes |
|---|---|
| `p256dh_encrypted` / `auth_encrypted` | Spec keys, Fernet-encrypted |
| `device_label`, `platform`, `user_agent` | Optional device metadata |
| `is_active` | Inactive devices never receive push |
| `failure_count`, `last_success_at`, `last_failure_at` | Delivery health |
| `revoked_at` | Soft remove / auto-deactivate |

Rules: inactive skipped · HTTP 404/410 or ≥5 failures auto-deactivates · user can list/remove devices · keys never returned to the client.

## Push outbox (`push_events`)

1. Product code calls `notify_user` / `enqueue_push` **after** payment verification (commerce)
2. Rows land as `pending` (or `skipped` if push off / prefs deny)
3. Worker: `python scripts/process_push_outbox.py` (defaults to `--loop --maintenance`)
4. Providers: `log` (safe) or `web_push` (pywebpush + VAPID)
5. Marks `sent` / `failed` / `skipped`; deactivates expired devices; logs **counts only**

Docker: `push_worker` in `docker-compose.yml` / `docker-compose.prod.yml`. Details: [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md#worker-command) · [OPERATIONS.md](./OPERATIONS.md).

## Push templates

Short copy in `backend/app/push/templates.py`. `notify_user` maps dotted in-app kinds → snake_case templates via `KIND_ALIASES` and `resolve_template_name()`.

**Channel registry:** `backend/app/notifications/channel_registry.py` lists user-facing kinds, default channels, critical/security flags, and documents intentional no-push exceptions. Full audit matrix: [NOTIFICATION_PUSH_AUDIT.md](./NOTIFICATION_PUSH_AUDIT.md).

| Area | Templates |
|---|---|
| Tickets | `ticket_confirmed`, `ticket_qr_ready`, `ticket_event_reminder`, `ticket_event_cancelled`, `ticket_event_updated`, `ticket_refund_update`, `ticket_transferred`, `ticket_transfer_accepted`, `ticket_checked_in` |
| Merch | `merch_order_confirmed`, `merch_pickup_ready`, `merch_shipping_update`, `merch_picked_up`, `merch_refund_update`, `post_event_drop_available`, `merch_cart_reminder`, `merch_vault_unlocked`, `merch_host_sale`, host ops (`merch_sold_out`, `merch_low_stock`, …) |
| Messaging | `new_message`, `message_request`, `attachment_received` |
| Fan Connect | `fan_connect_request`, `fan_connect_accepted`, `fan_connect_declined`, `fan_connect_removed`, `fan_connect_message` |
| Host | `host_ticket_sale`, `host_merch_sale`, `host_new_review`, `host_new_follower`, `host_sponsor_inquiry` |
| Support / account | `support_ticket_updated`, `account_suspended`, `account_appeal_decision`, `system_maintenance` |
| Vault | `vault_item_published` |
| Host team | `team_invite` (existing users / username invites), `team_invite_accepted`, `team_invite_revoked`, `team_member_removed`, `team_permission_updated`, `team_security_alert` |
| Ambassadors | `ambassador_joined`, `ambassador_first_sale`, `ambassador_commission_payable`, `ambassador_payout_ready`, `ambassador_campaign_paused`, `ambassador_campaign_ended`, `host_ambassador_milestone` (+ admin fraud via `admin_new_report`) |
| Sponsor | `sponsor_inquiry_confirmation`, `sponsor_inquiry_host_alert`, `sponsor_inquiry_status_update` |
| Admin | `admin_new_report`, `admin_payment_issue`, `admin_support_ticket`, `admin_push_test` |

Marketing-gated: `post_event_drop_available`, `merch_cart_reminder`.

Host team invite (`team_invite`) always emails. Username invites (and email invites to existing accounts) also enqueue in-app + push (`team.invite`) when prefs allow. Host receives `team_invite_accepted` (+ in-app/push) on accept. Overview: [TEAMS.md](./TEAMS.md#emails--notifications).

## Trigger channel matrix

When an important product event fires, keep channels aligned (`app/notifications/triggers.py`):

| Event | Email | Push | In-app |
|---|---|---|---|
| Ticket confirmed | yes (required) | if opted in | yes (+ QR ready notify) |
| Ticket QR ready | purchase covered by confirm email; regenerate may email | if opted in | yes |
| Fan ticket checked in | optional | if opted in (`push_ticket_updates`) | yes (`ticket.checked_in`) |
| Ticket refund update | yes | if opted in | yes |
| Merch pickup ready | yes (pref) | if opted in | yes |
| Host team invite / resend | yes (`team_invite`) | if invitee has account | if invitee has account |
| Host team accepted / revoked / removed / perms / suspend | matching `team_*` | if opted in | yes |
| New message | pref + **away only** | pref + **away only** | yes (toast via WS when online) |
| Fan Connect request | preference | preference | yes |
| Sponsor inquiry | yes | host preference | yes |
| Sponsorship deal proposal | yes | sponsor team | yes (`sponsor.deal_proposal`) |
| Sponsorship deal active (payment confirmed) | yes | host + sponsor | yes (`sponsor.deal_active`) |
| Deliverable submitted | yes | sponsor team | yes (`sponsor.deliverable_submitted`) |
| Deliverable approved / rejected | yes | host | yes |
| All deliverables complete | yes | both parties | yes (`sponsor.deliverables_completed`) |
| Admin report (review/message) | admin | admin preference | admin inbox |
| Ambassador joined / first sale / payable / payout ready | yes (pref) | if opted in | yes |
| Ambassador campaign paused / ended | yes (pref) | if opted in | yes |
| Host ambassador milestone | yes (`email_host_activity`) | if opted in | yes |
| Ambassador fraud click-spike | admin (`admin_new_report`) | admin preference | admin |

Ambassador prefs reuse ticket/host activity keys. Copy never includes buyer PII or payment refs — [AMBASSADORS.md](./AMBASSADORS.md#notifications-phase-15).

Message **away** = no active messaging WebSocket (local hub + Redis presence) and not subscribed to that thread. Live chat still uses `message.created` WS.

## Admin push settings

Page: `/admin/push/settings`

| Control | Behavior |
|---|---|
| Enable / disable | Global kill switch (`push_enabled`) |
| Provider mode | `log` (safe default) or `web_push` |
| VAPID keys | Generate or paste; private key Fernet-encrypted |
| Test push | Self or selected user/email; fixed copy (*Pàdéyá test notification* / *Push notifications are working.*); requires active device |
| Delivery / events | `/admin/push/deliveries`, `/admin/push/events` |
| Lookup | `/admin/push/subscriptions/lookup` |

Security: private key never returned to the frontend · public key only to clients · private key never logged. See [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md#vapid-setup).

## Preference keys

### Email (`user_email_preferences`)

| Key | Default | Can disable? |
|---|---|---|
| `email_security` | on | **No** |
| `email_ticket_updates` | on | Yes |
| `email_merch_updates` | on | Yes |
| `email_event_reminders` | on | Yes |
| `email_messages` | on | Yes |
| `email_fan_connect` | on | Yes |
| `email_sponsor_updates` | on | Yes |
| `email_host_activity` | on | Yes |
| `email_marketing` | on | Yes |

### Push (same table)

| Key | Default | Notes |
|---|---|---|
| `push_enabled` | on (master) | Off blocks **all** push, including security. Device must still subscribe. |
| `push_security` | on | Locked on; bypasses marketing opt-out |
| `push_ticket_updates` | on | Transactional; user may opt out |
| `push_merch_updates` | on | Transactional; user may opt out |
| `push_event_reminders` | on | |
| `push_messages` | on | Rate-limited (`PUSH_MESSAGE_RATE_LIMIT_PER_HOUR`, default 12) |
| `push_message_previews` | on | “Name sent you a message.” — never full chat text |
| `push_fan_connect` | on | |
| `push_sponsor_updates` | on | |
| `push_host_activity` | on | Sales / host ops (not reviews) |
| `push_reviews` | on | Review + review reply |
| `push_marketing` | on | User may opt out; also respects marketing unsubscribe |

UI: `/dashboard/settings/notifications`

## Always-send email

- Verified ticket / merch purchase confirmation (after Paystack webhook)
- Security emails

## Anti-spam rules

- Domain helpers use `notify_user` with dedupe keys where needed
- Messaging coalesces rapid same-thread alerts (~45s)
- Message push skipped when recipient has an active messaging WebSocket (presence)
- Popup ack prevents repeat toasts
- Push requires master `push_enabled` + category prefs (security locked when master on)
- Message-category push rate-limited per user/hour
- Marketing push respects category toggle + marketing unsubscribe
- Email remains a separate channel via `enqueue_template`

## Messaging WebSockets

Live chat remains REST-authoritative + WS fan-out. In-app/push are additional channels with generic copy only — they do not replace `/messages/ws`. Presence: local hub + Redis refcount (`app/messaging/presence.py`).
