# Blog taxonomy admin

Blog taxonomies (categories, tags, post types, media roles) are managed at
`/admin/blog/taxonomies` and documented in `docs/CRUD_MATRIX.md`.

## Permissions

| Permission | Capability |
|---|---|
| `admin.blog.view` / `admin.blog.edit` / `admin.blog.create` | Read taxonomies; select active terms on posts; keep archived terms already assigned |
| `admin.blog.taxonomy.manage` | Create, edit, reorder, archive, restore terms and media roles |

`admin.blog.edit` does **not** imply `admin.blog.taxonomy.manage`.

## Seeding

System post types and media roles are seeded by Alembic migration
`20260729_0210` and the idempotent helpers in `app.blog.taxonomy_service`
(also invoked from `seed_blog_content`). **GET endpoints never insert rows.**
Operators must not rely on first GET for seeding — run migrations (and optional
explicit seed) before serving traffic.

## Production build / homepage ISR

Public RSC fetches use bounded timeouts. During `next build`
(`PADEYA_SSG_ABORT_FETCH=1`), hung origins are aborted so SSG workers are not
held by orphaned sockets. Runtime ISR still uses `withTimeoutRace` without
AbortSignal so Next Data Cache / CDN behavior stays intact. Failed optional
homepage data falls back to empty rails; the hero and CTAs still render.

## Post-type identity

Authoritative identity is `post_type_id` + immutable `key`. Display `name` may
change without remapping. Studio briefs should store:

```json
{
  "post_type_id": "...",
  "post_type_key": "how_to",
  "post_type_name": "How-to guide"
}
```

`content_type` remains a legacy display mirror only.

## Media-role usage

`usage_count` / `display_usage_count` for `cover`/`og` count non-null post URLs.
Counts for `inline`/`gallery`/`social_share`/`teaser` are **approximate**
document scans and must not drive destructive cleanup.

Archive safety uses:

- `required_system_role` / `can_archive` (required core roles cannot archive)
- assignment validation (inactive terms blocked for new posts)
- soft archive only (no media deletion)

## Slug redirects

Category and tag slug changes require `confirm_slug_change=true` and write
`blog_taxonomy_slug_redirects` (chains collapsed). Public FE permanent-redirects
old slug → current slug.
