# Event Memories

Brand: **Pàdéyá** · API prefix: `/api/v1/memories`

Event Memories are a **post-event photo album** product — distinct from promotional **Event Gallery** (`event_media` on live event pages).

## Concepts

| Product | Model | When | Who |
|---|---|---|---|
| Event Gallery | `event_media` | Before / during | Host (Studio) |
| Event Memories | `event_memories` + `event_memory_media` | After start / completed | Host + verified ticket holders |

`EventMemory` is the album container (1:1 with event, auto-created on complete). Photos are `EventMemoryMedia` contributions with `uploader_role` `host` | `fan`.

## Limits

- Host: ≤ **10** active photos per event
- Fan: ≤ **5** active photos per user per event
- Fan eligibility: authenticated; ticket `buyer_user_id` **or** `claimed_by_user_id` in `active`/`checked_in`; `start_datetime <= now`; event status `published`/`paused`/`completed`

## Image pipeline

`app/memories/image_processing.py` (local media storage — no parallel provider):

1. MIME sniff JPEG/PNG/WebP (reject GIF/SVG)
2. Max raw upload 10MB
3. Decode + EXIF orientation + strip metadata
4. Resize longest edge ≤ 1800px
5. Encode WebP (~q80) + ~400px thumb WebP
6. Store under `memories/{event_id}/…` with generated keys

Do not claim production phone-upload performance until deployed and measured.

## Public routes

| Path | Notes |
|---|---|
| `/memories` | ISR hub — album cards only (no server `searchParams`) |
| `/events/{slug}/memories` | Album page; SEO only when `seo_indexable` |
| `/@{host}/memories/{slug}` | Legacy share URL → redirects to canonical |

## Host / fan / admin APIs

See `docs/API.md` and `backend/app/memories/router.py`.

Key endpoints:

- `GET /memories/albums`
- `GET /memories/events/{slug}`
- `GET /memories/events/{slug}/eligibility`
- Host multipart `POST /memories/host/events/{id}/photos`
- Fan multipart `POST /memories/events/{id}/photos`
- Host hide/restore attendee photo; admin hide/restore/remove

## Privacy

- Never expose ticket ID, order ID, email, phone, or payment data
- Fan attribution: Fan Passport `visibility=public` display name, else **Verified attendee**
- Hosts may hide attendee photos; cannot edit fan captions/images
- Fan Passport HTML remains no-store

## Cache / invalidation

- Public album GETs use short CDN TTL (see `cache_headers.py`)
- Host/admin/upload paths are no-store
- Mutations call `invalidate_memory_caches` → event cache invalidation

## Completed event UX

- `public_event_detail` allows `published` **or** `completed`
- Completed `/events/{slug}`: Past Event, no Buy tickets, Memories preview primary
- Upcoming events keep promotional Event Gallery + checkout

## External gallery

Optional `external_gallery_url` + `external_gallery_label` (`instagram` | `google_drive` | `official` | `other`). Validated http(s) only. Rendered as safe external link (no iframe).
