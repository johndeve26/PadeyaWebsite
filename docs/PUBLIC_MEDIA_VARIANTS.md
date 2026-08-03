# Public media variant pipeline

Brand: **Pàdéyá**

## Purpose

Server-side processing for public raster uploads. New uploads generate compressed
variants so grids never load multi‑MB originals, while lightboxes use a larger
bounded variant.

## Roles

Defined in `backend/app/public_media/roles.py`:

- `avatar`, `profile_cover`, `host_logo`, `host_cover`
- `event_cover`, `event_gallery`, `merch_product`
- `blog_cover`, `blog_inline`, `taxonomy_card`, `taxonomy_hero`
- `sponsor_logo`, `sponsor_cover`, `memory`, `social_og`, `general`

## Variants

| Variant | Typical long edge | Use |
|---------|-------------------|-----|
| thumbnail | ~320 (avatars ~160) | dense grids, nav |
| card | ~720–960 | listing cards |
| display | ~1600–1920 | detail / hero |
| full | ~2200–2560 | lightbox |
| og | 1200×630 | social cards where required |

Never upscale beyond source dimensions. Photographic roles emit WebP.
Logo roles preserve alpha (lossless WebP).

## Source retention

Source bytes are stored under an unguessable `…/source/` key on the public
bucket. Public API responses **never** include `source_key` or `_storage_keys`.
Use `public_media_response()` before returning HTTP payloads.

## Storage keys

Immutable UUID keys under:

`public-media/{owner_type}/{owner_id}/{asset_id}/…`

Replacement always creates a new asset; CDN objects are not overwritten.

## API shape

```json
{
  "id": "…",
  "role": "event_cover",
  "url": "<display>",
  "thumbnail_url": "…",
  "card_url": "…",
  "display_url": "…",
  "full_url": "…",
  "og_url": "…",
  "variants": { "thumbnail": { "url": "…", "width": 320, "height": 213 }, "…" : "…" }
}
```

Legacy string URL fields remain populated with the **display** URL.

## Frontend

- Types/helpers: `frontend/src/lib/types/public-media.ts`, `frontend/src/lib/public-media.ts`
- Component: `PublicMediaImage` + `Media` (`enlargeSrc` for lightbox)
- Fallback: requested → nearest larger → legacy URL

## Animation policy

Ordinary public roles flatten the first GIF/WebP frame. Do not upload animation
for avatars/covers/products expecting motion.

## Backfill

```bash
cd backend
python -m app.public_media.backfill --dry-run --limit 50
python -m app.public_media.backfill --limit 50
```

Do not run inside Alembic. Only storage-origin URLs are processed.

## Adding a role

1. Add `MediaRole` + `MediaRolePolicy` in `roles.py`
2. Map upload kind in `map_upload_kind_to_role`
3. Wire the upload path through `process_and_store_public_media`
4. Persist companion JSON (`*_media`) + display URL on the domain model
5. Teach FE helpers / surfaces to prefer variants with legacy fallback
6. Add processor + surface tests
