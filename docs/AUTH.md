# Auth

Authentication, sessions, and admin impersonation for Pàdéyá.

Related: [SECURITY.md](./SECURITY.md) · [ADMIN.md](./ADMIN.md) · [ROLES_AND_PERMISSIONS.md](./ROLES_AND_PERMISSIONS.md) · [API.md](./API.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [COOKIES_AND_STORAGE.md](./COOKIES_AND_STORAGE.md).

## Normal login

- Register / login issue a **JWT access token** + **hashed refresh token** (rotated on refresh).
- Default lifetimes (env/config): **access ~30 minutes**, **refresh ~180 days**. Each successful refresh rotates the refresh token and starts a new refresh window (persistent “stay signed in” on the device).
- Passwords are bcrypt-hashed; never returned by the API.
- RBAC loads roles/permissions from the database for the authenticated user.
- Frontend stores tokens in **localStorage** and sends `Authorization: Bearer` on API requests; logout revokes the refresh token. See [COOKIES_AND_STORAGE.md](./COOKIES_AND_STORAGE.md) (not HTTP auth cookies).
- On startup the app **silently refreshes** when the access token is missing or near expiry before treating the user as logged out. API calls retry once after refresh on `401`.
- Sessions end on explicit logout, refresh revocation (password/email change, admin force-logout, suspend/ban), refresh expiry, or cleared site data.

**Future hardening (not implemented):** httpOnly Secure cookies for tokens — evaluate separately; see [COOKIES_AND_STORAGE.md](./COOKIES_AND_STORAGE.md).

Routes: `/login`, `/register` · API: `POST /api/v1/auth/register`, `/login`, `/refresh`, `/logout` · `GET /api/v1/auth/me`.

## Session identity

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/auth/me` | Current user profile (+ `impersonation` block when active) |
| `GET /api/v1/me/session` | `current_user_id`, `actor_admin_id`, `impersonation_id`, `is_impersonating` |
| `GET /api/v1/me/impersonation` | Impersonation status for the active token |

While impersonating: **current user = target**; **actor admin** is stored separately and never mixed into target RBAC.

## Admin user impersonation

**Internal support/QA only** — an audited temporary view of Pàdéyá as a specific user. It is **not** a real login as that user. The target user is **never** notified (no email, in-app, or push).

| Guarantee | Behavior |
| --- | --- |
| **Internal and audited** | Support/QA workflow only. Every start / end / expiry / sensitive block / request stamp is logged. |
| **Target user is not notified** | No email · no in-app · no push when impersonation starts or ends. |
| **No password access** | Admin never reads, returns, or shares the target’s password. |
| **No session hijacking** | Target refresh tokens are not reused, revoked, or rotated. Impersonation issues a **separate** short-lived access token only (no refresh). |
| **Sensitive actions blocked** | Password/email/phone/2FA, bank/payouts, checkout, ticket transfer, content delete, Passport privacy, social/Fan Connect, provider keys, admin/support/finance → `403` `This action is disabled during admin impersonation.` Allowlist: view dashboard/tickets/orders/Passport/Vault; reproduce navigation. |
| **Max duration** | Allowed `15` / `30` / `60` minutes; **default 30**, **max 60**. Auto-expires; one active session per admin. |
| **Permission required** | `admin.users.impersonate` (`super_admin` via `admin.full_access`; support/finance only with explicit grant). Buyers, host owners, and host team members cannot impersonate. |
| **Admin / session separation** | Admin tokens stay stashed in the browser; Exit restores them. JWT + DB session keep `actor_admin_id` distinct from `current_user` (target). Admin permissions never leak. `/admin` is blocked while impersonating. |
| **Audit logs retained** | Domain `admin_impersonation_audit_logs` + platform `audit_logs`. Actions: `admin_impersonation_started` / `_ended` / `_expired` / `_sensitive_action_blocked` / `_request_made`. Fields: `impersonation_id`, actor admin, target, `path`/`method`, reason, support ticket (if any), `ip`/`ua`/`created_at`. No request bodies or secrets. Never skipped in demo mode. Banner is admin-visible only. |

### Token claims (impersonation access token)

Required session claims:

| Claim | Value |
| --- | --- |
| `actual_user_id` | Target user |
| `actor_admin_id` | Admin user |
| `impersonation_id` | Session id |
| `is_impersonating` | `true` |
| `started_at` | Session start (ISO) |
| `expires_at` | Session expiry (ISO) |
| `reason` | Required start reason |

Also present: `sub` (= target), target-only `roles` / `permissions`, optional `support_ticket_id`. Admin permissions never appear in the token.

### Session rules

- **Current user** behaves as the target (`/auth/me`, RBAC from target DB rows).
- **Actor admin** remains stored separately (`actor_admin_id` on JWT, `/me/session`, audit).
- **Admin permissions must not leak** into the impersonated session.
- **`/admin` is blocked** while impersonating (API middleware + FE `denyWhileImpersonating`).
- **No nested impersonation** (start while already impersonating → 403).
- **Duration:** default **30** minutes; allowed `15` / `30` / `60`; max **60**.
- **Expire automatically** (JWT `exp` + DB session check → 401).
- **End on logout** (`POST /auth/logout` ends the DB session).
- **End on Exit** (`POST /admin/impersonation/end`; FE restores stashed admin tokens).

### Frontend behavior

- Start from `/admin/users/[userId]` (modal) after reason + confirmation.
- Global `ImpersonationBanner` (root shell) with Exit; demo seeds show **Demo seed account**.
- Personal `/dashboard` renders as the target; `/host` only if the target has host access; Passport privacy settings UI is locked during the session.

Full product tables: [SECURITY.md](./SECURITY.md#admin-user-impersonation) · [ADMIN.md](./ADMIN.md#user-impersonation).
API: [API.md](./API.md#admin-user-impersonation). Schema: [DATABASE.md](./DATABASE.md#admin-user-impersonation).
