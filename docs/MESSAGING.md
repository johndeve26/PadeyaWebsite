# In-app messaging (Pàdéyá)

Privacy-first **fan ↔ host** inbox. Conversations stay on Pàdéyá — no phone, email, or WhatsApp by default.

## Principles

Messaging should feel normal and modern (bubbles, replies, pins, stars, status), but **permissions stay strict**.

1. No email / phone / WhatsApp exposed in messaging UIs or serializers  
2. Messages stay in-app  
3. Users can block and report (**not** themselves)  
4. Hosts cannot mass-DM random fans (including Fan Passport Directory-only fans)  
5. Admins review reported threads only  
6. Notifications never include full message bodies by default (Fan Connect uses the same list — request/accept/message kinds without private event details)  
7. Attachment messages use safe copy only (“You received a new message with an attachment on Pàdéyá.”) — never file contents or private download URLs in email/in-app  
8. Users cannot create a fan↔fan thread with themselves  

### Chat feature invariants

| Feature | Rule |
|---------|------|
| **Fan ↔ host** | Own relationship gates only — never Fan Connect rules; **owner cannot message own host** from Personal ([HOST_AS_FAN.md](./HOST_AS_FAN.md)) |
| **Fan ↔ fan** | Connection-only (`connected`); removed/blocked disables send; **no self threads** |
| **Pins** | Shared per thread; both participants see the same pins; WS `message.pinned` / `unpinned` |
| **Stars** | Private to the viewer; peer never sees or gets notified; no star WS |
| **Replies** | Same-thread + `can_send_message` + safe sanitized preview; hidden/deleted → unavailable |

## Who can message whom

### Fan → host

Allowed when the host is active and messaging is enabled, and the fan is not blocked. Strong relationships (follow / ticket / check-in) open an **active** thread. Weaker public contact may create a **message request** (rate-limited).

**Own-host exception (Host-as-Fan):** the **host owner** cannot open Personal fan→host messaging against **their own** host. Guard: `assert_not_own_host_fan_messaging` — “You can’t message your own host workspace from your Personal account.” (403). Host A may still message Host B normally. Team/staff may message that host as fans when otherwise allowed. Public own-host UI hides Message and shows **Open Host workspace** instead. See [HOST_AS_FAN.md](./HOST_AS_FAN.md).

**Message Host** CTA (`StartMessageButton`) on Legacy / event pages: logged-out users go to `/login?next=…`; existing `(fan, host)` threads are reused (one thread per pair); own-host owners never see a working Personal Message CTA for their own host.

### Host → fan

Allowed only with a real relationship:

- fan follows host  
- fan bought a ticket from host  
- fan checked in  
- fan reviewed host  
- open conversation already exists  

**Not** allowed solely because a fan appears in the Fan Passport Directory.

**Message Fan** CTA (`HostMessageFanButton`) on public/unlisted Passports only — hidden unless `GET /host/messages/can-message-by-username/{username}` allows.

### Fan ↔ fan (`thread_type = fan_fan`)

Only via **Fan Connect**. Rules:

- Thread created/unlocked **only** when a connection is accepted (`status=connected`)
- No messages before accept; blocked / removed connections cannot send
- **Users cannot message themselves** — `ensure_fan_fan_thread` / messaging block reject self with “You can’t message yourself.” / “You can’t block yourself.”
- Accept posts a system line: `You connected through [safe reason] on Pàdéyá.`
- Fan inbox (`/dashboard/messages`) lists `fan_fan` threads with a **Fan Connect** badge and safe context (e.g. “Connected through Product Demo Night”) — never VIP, spend, private events, or hidden venues
- Threads use `fan_user_id` + `fan_b_user_id` (canonical high UUID); `host_id` is null
- Own Fan Passport hides Message (and Connect); visitors still see Message only when Connect unlocks a thread — [FAN_PASSPORT.md#own-fan-passport](./FAN_PASSPORT.md#own-fan-passport)

**Two admin surfaces (do not conflate):**

| Surface | What it covers |
|---------|----------------|
| `/admin/fan-connect/reports` | Fan Connect **user / connection** reports (`fan_connection_reports`) — safe connection context only; does **not** open unreported chats |
| `/admin/message-reports` | Reported **message threads** (including `fan_fan`) — hide/restore bodies when a fan reports the thread via messaging |

See [FAN_CONNECT.md](./FAN_CONNECT.md).

## Thread statuses

`active` · `request` · `archived` (per-participant `fan_archived_at` / `host_archived_at`) · `blocked` · `reported` · `closed`

Inbox filters: `all` · `unread` · `requests` · `event` · `archived`. Filter `all` excludes the viewer’s archived threads; archived remain readable via `?filter=archived` or direct thread URL.

## Routes

| Surface | Path |
|---------|------|
| Shared redirect | `/messages`, `/messages/[threadId]` |
| Fan inbox | `/dashboard/messages`, `/dashboard/messages/[threadId]` |
| Fan settings | `/dashboard/messages/settings` |
| Fan notifications | `/dashboard/notifications` → `/dashboard/messages/notifications` |
| Host inbox | `/host/messages`, `/host/messages/[threadId]` |
| Host settings | `/host/messages/settings` |
| Host notifications | `/host/messages/notifications` |
| Admin (message reports) | `/admin/message-reports`, `/admin/message-reports/[id]` |
| Admin (Connect reports) | `/admin/fan-connect/reports` — connection reports, not chat browse |
| Demo QA | `/demo` (one-click inbox + Fan Connect shortcuts) |

## Real-time delivery (WebSocket)

**Endpoint:** `WS /api/v1/messages/ws?token=<access_jwt>`

**REST remains the send authority** — clients never upload files or create messages over the socket.

| Item | Detail |
|------|--------|
| Auth | JWT required on connect; invalid/expired/inactive → close `4401` |
| Connection | One socket per client tab; auto-subscribed to personal user channel |
| Thread channel | Optional `thread.subscribe` / `thread.unsubscribe` after participant check |
| Multi-worker fan-out | Redis pub/sub when `REDIS_URL` is reachable (`/health` → `messaging_ws_fanout=redis`) |
| In-memory fallback | If Redis is down (or `APP_ENV=test`), fan-out is **in-process** — **single API worker only** |
| Client unread fallback | `useUnreadRealtime` polls `GET /messages/unread-count` (90s while live, 20s when offline) |

### Client reconnect behavior

Implemented in `frontend/src/lib/messaging/message-socket-client.ts` (+ `MessagingSocketStatus` UI):

| Behavior | Detail |
|----------|--------|
| Statuses | `connected` · `reconnecting` · `offline` |
| Keepalive | Client `ping` every **25s** → server `pong` |
| Backoff | On unexpected close: exponential `min(30s, 1s × 2^retry)` then reconnect |
| Auth close | Codes `4401` / `1008` → refresh access token, then reconnect (else `offline`) |
| Intentional close | Logout / disable → no reconnect |
| Dedupe | Client + server suppress duplicate fan-out (user + thread channels) |
| Live UI | Inbox merges `message.created` / `thread.updated` without full reload; typing + unread badge update live |

Multi-worker or multi-host deployments **must** run Redis so a user on worker A still receives events created on worker B.

### Redis pub/sub (multi-worker)

When Redis is available, workers publish sanitized envelopes to:

- `user:{user_id}:messages` — inbox / participant delivery
- `thread:{thread_id}:messages` — optional active-thread subscribers

Each worker subscribes only to channels for users (and threads) that have local sockets. Local delivery dedupes if the same payload arrives on both channel types.

**Privacy:** message bodies and attachment URLs only for **authorized thread participants**. `attachment.ready` is uploader-only. `thread.updated` carries preview text only (never a full body). Redis payloads are sanitized again before publish (no email/phone/shipping/order/payment/hidden venue fields).

### WebSocket permissions (server-enforced)

Gates run on **publish** and again on **local delivery**. Frontend checks are never trusted.

| Rule | Behavior |
|------|----------|
| fan ↔ host | Only the fan party and host party of that thread receive events |
| fan ↔ fan | `thread_type=fan_fan`; active events only while Fan Connect is `connected` |
| Blocked | No active events (`message.*` content/typing/read, `thread.updated`); `thread.disabled` / `connection.removed` still delivered so UI can lock |
| Connection removed / thread closed | Active events blocked; lifecycle events allowed for participants |
| Reported | Follow existing moderation/REST rules (participants still scoped; redaction via serializers) |
| Admin | Role alone does **not** join private threads over WS; admins use REST moderation/report surfaces |

Client actions (`typing.*`, `message.read`, `thread.subscribe`) use the same emit gates.

### Server → client events

| Event | When |
|-------|------|
| `connected` / `pong` | Connect / keepalive |
| `message.created` | REST send (participant-scoped body + safe attachments) |
| `message.updated` | Delivered status / admin restore |
| `message.deleted` | Admin hide (redacted payload) |
| `message.read` | Peer marked thread read (`reader_id` + `read_at`; thread-level cursor) |
| `message.typing` | Peer typing (ephemeral; `display_name` only — no DB persist, no contact fields) |
| `thread.updated` | Inbox list preview / request lifecycle / unread clear on mark-read |
| `thread.unread_count_updated` | Sidebar badge after send / mark-read |
| `thread.disabled` | Block / report / remove |
| `connection.accepted` | Fan Connect accept → `fan_fan` ready |
| `connection.removed` | Fan Connect remove / block |
| `attachment.ready` / `attachment.failed` | Upload result (uploader only) |
| `message.pinned` / `message.unpinned` | Shared pin list changed (`pinned_messages` summary) |
| `thread.subscribed` / `thread.subscribe_denied` / `thread.unsubscribed` | Subscribe acks |

Constants: `backend/app/messaging/ws_events.py` ↔ `frontend/src/lib/messaging/socket-types.ts`.

### Client → server events

| Event | Behavior |
|-------|----------|
| `ping` | → `pong` |
| `typing.start` / `typing.stop` | Ephemeral; participant + can-reply gated; **peers only** (not echoed to sender). Legacy aliases `typing` / `typing_stop` accepted |
| `message.read` | Same gates as REST `PATCH …/read`; only marks the authenticated user’s cursor |
| `thread.subscribe` / `thread.unsubscribe` | Optional active-thread channel |

### Typing indicators

- Ephemeral only — never persisted as `messages` rows
- Debounced start / idle stop on the client (`useTypingIndicator`)
- Payload: `thread_id`, `user_id`, `is_typing`, optional safe `display_name` (no email/phone/username leak on `fan_fan`)
- UI copy: “{name} is typing…” (`formatTypingLabel`)

### Read receipts & unread (thread-level)

Uses `message_threads.fan_last_read_at` / `host_last_read_at` (no per-message `message_read_receipts` table).

| Rule | Behavior |
|------|----------|
| Who can mark read | Authenticated participant of that thread only (REST or WS) |
| Spoofing | Client `reader_id` / `read_at` ignored; server stamps the socket/REST user |
| Receipt fan-out | `message.read` → **other** participants only |
| Reader UI | `thread.updated` with `unread: false` + `thread.unread_count_updated` for sidebar/badge |
| Hydration | Thread detail includes `peer_read_at` for **Read** labels on reload |
| Bubble labels (own) | `Sent` → `Delivered` (peer online via WS) → `Read` (thread cursor ≥ message time); `Failed` on client send failure; `Edited` when `edited_at` set. Never invent Read/Delivered. |
| Badge API | `GET /messages/unread-count` (+ live WS updates via `useUnreadRealtime`) |

## Safe attachments (v1)

### Upload flow

1. Client validates type/size (`attachment-limits.ts`) → `POST …/threads/{thread_id}/attachments` (multipart `file`)
2. Server re-validates → stores privately → row `pending` → `ready` / `rejected` / `failed` (**no chat message yet**)
3. Optional uploader-only WS: `attachment.ready` / `attachment.failed`
4. Client sends `POST …/{thread_id}/send` with `attachment_ids` (same thread, status=`ready`); body may be empty only when ≥1 attachment
5. Peers receive `message.created` with allowlisted attachment metadata + authorized download URL

| Item | Detail |
|------|--------|
| Fan upload | `POST /api/v1/messages/threads/{thread_id}/attachments` |
| Host upload | `POST /api/v1/host/messages/threads/{thread_id}/attachments` |
| Not over WS | Files never upload via WebSocket |
| Download | `GET /api/v1/messages/attachments/{attachment_id}` — Bearer **or** short-lived `?d=` signed token (TTL `MESSAGING_ATTACHMENT_DOWNLOAD_TTL_SECONDS`, default 900s) |
| Orphans | Unbound rows expire after `MESSAGING_ATTACHMENT_ORPHAN_HOURS` (default 24h); sweeper + `python -m scripts.cleanup_message_attachments` |

### Allowed types & size limits

| Allowed | Rejected |
|---------|----------|
| JPEG / PNG / WebP · PDF · `text/plain` · CSV · DOCX | SVG, HTML, ZIP/archives, executables/scripts, unknown binaries, MIME/extension/content mismatches |

| Limit | Default | Env |
|-------|---------|-----|
| Image | 5 MB | `MESSAGING_ATTACHMENT_MAX_IMAGE_BYTES` |
| Document | 10 MB | `MESSAGING_ATTACHMENT_MAX_DOC_BYTES` |
| Total per message | 15 MB | `MESSAGING_ATTACHMENT_MAX_TOTAL_BYTES` |
| Count per message | 4 | `MESSAGING_ATTACHMENT_MAX_COUNT` |

### Storage provider design

| Item | Detail |
|------|--------|
| Provider | `MESSAGING_ATTACHMENT_STORAGE_PROVIDER` = `local` (default) · `s3` / `r2` stubs (not configured until credentials exist) |
| Local root | `MESSAGING_ATTACHMENT_STORAGE_ROOT` (default `storage/message_attachments/`, gitignored) |
| Keys | Server-generated `{thread_id}/{uploader_id}/{uuid}{ext}` — never user-controlled paths |
| Public access | **Never** under `/media` or static file mounts |
| Interface | `AttachmentStorage.store` / `open_bytes` / `delete` / `exists` (`attachment_storage.py`) |

### Attachment permissions

| Rule | Behavior |
|------|----------|
| fan ↔ host | Participant + not blocked; same gates as send |
| fan ↔ fan | Accepted Fan Connect only (`connected`, not removed/blocked) |
| Message requests | **No attachments** until accepted/`active` — thread detail exposes `can_attach` |
| Blocked / closed | Upload + bind denied |
| Admin | View/download **only** when a `message_reports` row exists for the thread — not a private-file browser |

### Moderation / reporting

| Surface | Behavior |
|---------|----------|
| Participant report | `POST …/report` → thread may become `reported`; system notice |
| Admin message reports | `/admin/message-reports` — status, hide/restore message, attachment moderation |
| Attachment actions | `PATCH /admin/messages/attachments/{id}/hide\|restore\|delete\|review` (audited) |
| Soft-delete | `deleted_at` + status; **bytes retained** by default (no hard delete) |
| Hide message | Also soft-hides ready attachments on that message |
| Download after hide/delete/reject | Participants get 404; admin may still access reported-thread files when policy allows |

### File safety & privacy

| Item | Detail |
|------|--------|
| Validation | Size, extension, MIME, magic bytes, SHA-256; sanitized display filename |
| Images | Pillow verify + dimensions; EXIF/ICC strip (`MESSAGING_ATTACHMENT_STRIP_IMAGE_METADATA`) |
| PDF / docs | Served as `Content-Disposition: attachment` (not unsafe inline HTML) |
| Antivirus | **Not scanned in v1** — `MESSAGING_ATTACHMENT_SCANNER=noop` (ClamAV hook reserved) |
| Public payload allowlist | `id`, `url`, `content_type`, `byte_size`, `original_filename`, `width`/`height`, `status`, optional `reviewed_at` (moderation view) |
| Never exposed | `storage_key`, FS paths, checksums, EXIF/GPS, uploader ids, rejection internals, phone/email, venue/order/payment fields |
| Signed URLs | Viewer-scoped HMAC query tokens — not a substitute for auth on anonymous browsing |

## Chat features (edit / reply / pin / star)

REST chat actions live in `app.messaging.chat_actions` and **must** go through the shared permission layer in `app.messaging.permissions`:

| Helper | Used for |
|--------|----------|
| `can_read_thread` / `assert_can_read_thread` | Thread access (participant) — list pins, search, star/unstar, unpin |
| `can_send_message` / `assert_can_send_message` | Send + thread `can_reply` (fan↔host / fan↔fan gates) |
| `can_edit_message` / `assert_can_edit_message` | Own-body edit within window |
| `can_pin_message` / `assert_can_pin_message` | Pin / unpin |
| `can_star_message` / `assert_can_star_message` | Personal star |
| `can_reply_to_message` / `assert_can_reply_to_message` | `reply_to_message_id` on send |
| `can_delete_message_for_me` / `assert_can_delete_message_for_me` | Soft delete-for-me |

Fan↔host and fan↔fan rules are unchanged: fan_fan messaging only after accepted Fan Connect; removed/blocked connection disables messaging. Migrations: `0055` reply/pins/stars → `0056` edit history → `0057` soft unpin → `0058` soft unstar → `0059` `message_deletions`.

| Feature | Behavior |
|---------|----------|
| **Edit** | Sender-only within **24h**; text body only (attachments unchanged); requires `can_send_message`; system/hidden/deleted denied; sets `edited_at` + `edit_count`; WS `message.updated` (+ `thread.updated` if latest preview); admins never edit bodies — hide/restore only |
| **Edit history** | Append-only `message_edits` (`previous_body`, `new_body`, `editor_user_id`, `edited_at`). Retained for audit/moderation — **not** a participant-facing history UI |
| **Reply** | Single-level quote via `reply_to_message_id` on send; same-thread text/image/attachment only; composer `ReplyPreview`; bubble `QuotedMessage`; permission-checked (`assert_can_reply_to_message`); deleted/delete-for-me → “Original message unavailable”; moderated → “Message unavailable”; cross-thread → unavailable |
| **Pin** | **Shared** per thread (both participants); max **3** active; either participant may pin/unpin while pin gate allows; system msgs OK; soft `unpinned_at`; hide/delete auto soft-unpins; WS `message.pinned` / `unpinned` + `thread.updated`; UI `PinnedMessagesBar` |
| **Star** | **Personal** (`message_stars`); peer never sees or is notified; soft `unstarred_at`; inbox `?filter=starred` + `GET /messages/starred`; hidden/deleted redacted; no star WS (optimistic FE only) |
| **Read / status** | Thread-level cursors only (`peer_read_at`); own bubbles: Failed → Read → Delivered → Sent + Edited — never invent receipts (see [Read receipts](#read-receipts--unread-thread-level)) |
| **Search** | In-thread only: `GET …/threads/{id}/search?q=&starred=&pinned=&has_attachments=` — body `ILIKE` (escaped), excludes hidden/deleted; no FTS; click scrolls + highlights |
| **Actions** | `MessageActionMenu` / long-press `MessageContextMenu`: own → Reply · Edit · Star · Pin · Copy · Delete for me · Report; peer → Reply · Star · Pin · Copy · Delete for me · Report · Block; system → Star · Pin. Unavailable actions hidden |
| **Delete for me** | Soft `message_deletions` (`for_me`); peer still sees; no hard delete; `for_everyone` blocked; soft-unstars; excluded from pins/search/reply previews for that viewer |

## Timestamps (display-only)

ISO `created_at` / `last_message_at` from the API are authoritative. FE formats with `en-NG` + browser local timezone (`format-message-time.ts`).

| Surface | Rules |
|---------|-------|
| Bubble | Today `2:35 PM` · Yesterday `Yesterday, 2:35 PM` · same year `Jul 18, 2:35 PM` · prior year `Jan 12, 2026, 2:35 PM` — always visible on mobile; desktop reveals on row hover/focus |
| Thread list | `now` · `5m` · `2h` · `Yesterday` · `Jul 18` |
| Day separators | `Today` · `Yesterday` · `Friday, Jul 18` · `Jan 12, 2026` |

## Frontend display

Inbox list/detail show counterpart name + avatar, relative time, last-message preview, unread / request / archived / reported / blocked badges, **Fan Connect** badge + connection context for `fan_fan`, related-event chip or mini-card (`RelatedEventMiniCard`), system messages, privacy reminder, report/block, and request banner (“Message request”) with Accept for hosts. Starred filter lists personal saved messages (`StarredMessagesList`).

Chat UI building blocks (`frontend/src/components/messaging/`): `MessageBubble` · `MessageTimestamp` · `MessageStatus` · `MessageMeta` · `MessageActionMenu` / `MessageContextMenu` · `QuotedMessage` · `ReplyPreview` · `MessageEditComposer` · `PinnedMessagesBar` · `ThreadSearch` · `DateSeparator` · `StarredMessagesList`.

**Composer attachments:** attach button + file picker, client validation, per-file upload progress, image/doc previews, remove before send. Attach control only when `can_attach` (hidden for message requests / blocked / closed). Errors: too large, unsupported type, upload failed, rejected, not allowed in thread. Reply chip (`ReplyPreview`) + edit mode (`MessageEditComposer`) supported.

**Bubbles:** clock (always on mobile; hover/focus on desktop) · Edited (any message) · Sent/Delivered/Read/Failed (own only, real delivery + thread-level `peer_read_at`); quoted reply; pin/star markers; action menu (··· / long-press / context menu). Smooth scroll + brief highlight for reply/pin/search/`?m=` targets. Images show thumbnail + filename + size; PDFs/docs show a compact file row. Mobile: picker usable, previews capped, bubbles `min-w-0` / truncate. Day separators between calendar groups; pinned bar above the scroll.

**Thread list:** counterpart · latest timestamp · latest preview (editing the latest message updates the preview text) · unread indicator (cursor-based; not a fabricated per-message tally).

**Realtime hooks:** `useMessageSocket` (shared client) · `useThreadRealtime` (thread subscribe + merge including pin/edit) · `useTypingIndicator` · `useUnreadRealtime` · `MessagingSocketStatus` (connected / reconnecting / offline). Dark mode + mobile list/detail split are supported.

## API (selected)

See [API.md](./API.md#messaging) for the full table.

| Area | Paths |
|------|--------|
| Fan | `GET/POST /messages…`, `…/threads`, `…/{id}/send`, edit/pin/star, `GET /messages/starred`, attachments, archive, accept, report, block |
| Host | `GET/POST /host/messages…`, can-message helpers, send, edit/pin/star, starred, attachments, archive, report, block |
| Realtime | `WS /messages/ws` |
| Settings | `GET/PATCH /messages/settings` — includes `blocked_users` (display names only) |
| Unread | `GET /messages/unread-count` |
| Notifications | `GET /messages/notifications` — WS `message.created` for live delivery; in-app row coalesced (~45s/thread); attachment-safe copy; email only if a messaging email preference exists (none today) |
| Admin | `GET/PATCH /admin/message-reports`, hide/restore message, `PATCH /admin/messages/attachments/{id}/hide|restore|delete|review` |

### Serializer privacy

- **Participant:** `display_name`, optional `username` / avatar / Legacy or Passport path — never email or phone.  
- **Related event chip:** `id`, `title`, `slug`, `path`, optional `banner_url` only.  
- **Thread detail:** no `related_order_id` / `related_ticket_id` in public payload.  
- **Messages:** body and attachment URLs redacted when hidden/deleted by moderation.  
- **Settings `blocked_users`:** `user_id`, display name, username — no contact fields.
- **WS payloads:** same privacy rules as REST `MessagePublic` / inbox preview fields.

## Privacy (never expose)

Never return to participants (or smuggle via reply/pin/star/search/WS):

- phone, email, WhatsApp / contact fields  
- hidden event locations / private venue addresses  
- private attendee data, ticket type  
- spend / order / payment data  
- shipping address  
- locked Vault content  
- storage keys / private file paths / checksums  

**Reply previews** (`_reply_to_public`): same-thread only; delete-for-me / hidden / deleted → unavailable placeholder; attachment labels use sanitized display filenames only.

**Pins / stars / search:** hidden or deleted content is redacted or omitted; inbox `last_message_preview` redacts hidden/deleted last messages; search does not ILIKE-match hidden/deleted bodies; starred list drops rows the viewer can no longer read.

**Blocked / removed / reported:** sending disabled (`can_send_message`); pin/edit follow the same send gate. Reported threads pause compose (REST + WS).

Demo seed copy uses safe placeholders only (see [DEMO_DATA.md](./DEMO_DATA.md) and `app/demo/messaging_privacy.py`).

Do not encourage moving conversations outside Pàdéyá.

## Admin moderation

Private chats are **not** browsable by admin role alone.

| Action | Rule |
|--------|------|
| Open thread content | Only via **message reports** (`GET /admin/message-reports/{id}`) |
| Hide / restore message | `PATCH /admin/messages/{id}/hide\|restore` — requires a `message_reports` row on that thread; audited; clears pins; redacts body for participants; updates inbox preview when last message |
| Attachment hide/restore/delete/review | Same report scope; soft statuses; bytes retained by default |
| Edit participant bodies | **Never** — admins do not use the edit path |
| Fan Connect reports | Separate surface (`/admin/fan-connect/reports`) — does not unlock chat browse |

Report list/detail omit payment/location secrets and contact patterns. Serializers in moderation view may show attachment metadata but never `storage_key` / paths.

## Demo data

Seeded by `app/demo/messaging_seed.py` (via `seed_demo_data`). Idempotent; blocked when `APP_ENV=production`.

Safe attachment placeholders (PNG/PDF) are generated by `app/demo/messaging_attachments_seed.py` for Chidi↔Bayo, Tolu↔DJ Maze (public entry-flow only — no private venue maps), and the Bayo↔Tech reported thread (admin moderation QA).

Chat feature demos (edit / reply / pin / star / read cursors) are applied by `app/demo/messaging_chat_features_seed.py`. `/demo` shortcuts open Tolu↔DJ Maze, Chidi↔Bayo, Starred messages, and the pinned-message demo.

Full account matrix, inbox QA states, report examples, and reseed commands: **[DEMO_DATA.md](./DEMO_DATA.md)**.

Backend privacy contract tests: `tests/test_demo_messaging_privacy.py`.

Phase 19 checklist coverage (WS auth/fan-out/typing/read/dedupe, attachment allow/deny/download/moderation, privacy redaction): `tests/test_messaging_phase19.py` plus `tests/test_messaging_realtime_attachments.py`, `tests/test_messaging_ws_permissions.py`, `tests/test_messaging_attachments_validate.py`, `tests/test_messaging_attachment_privacy.py`, `tests/test_messaging_ws_bus.py`.

Phase 20 frontend contract smoke: `npm run test:messaging` (`frontend/scripts/messaging-attachments-smoke.mjs`) — composer attach/preview/progress/remove, bubbles, `can_attach` / Fan Connect gates, WS typing/unread/reconnect, mobile + light/dark tokens.

## Out of scope / future (not built)

| Out of scope now | Notes |
|------------------|-------|
| Per-message read receipts table | Thread-level cursors + WS `message.read` only |
| Public edit-history UI / reactions / forward | History stored in `message_edits` (not participant UI) |
| Voice notes / voice-video calls | — |
| Live location / proximity map | — |
| Phone / WhatsApp sharing UX | Conversations stay on Pàdéyá |
| Antivirus scanning | Hook reserved (`noop`); ClamAV not wired |
| Cross-worker online presence | Local socket presence only |
| Public group chats / host broadcast | — |
| Private attendee lists | — |
| S3/R2 production storage | Provider stubs only until credentials + implementation |

PDF/DOCX/text attachments, Redis multi-worker fan-out, typing, and private local storage **are shipped** in v1.
