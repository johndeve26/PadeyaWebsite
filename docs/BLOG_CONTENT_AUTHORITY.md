# Blog content authority

## Modes

| Mode | When | Authoritative field | Derived fields |
|------|------|---------------------|----------------|
| `legacy` | No `content_document`, or single `legacy_rich_text` wrapper | `body` (markdown) | `body_html` via markdown → sanitize |
| `block_document` | Valid block `content_document` (not legacy-only) | `content_document` | `body` (markdown export), `body_html` (block renderer) |

## Save rules

### Autosave / document PATCH

- When `content_document` is included in the request, the server validates it and **ignores** any client `body`.
- When a post is already in `block_document` mode and the request omits `content_document`, the server **re-derives** `body` from the stored document (client `body` is ignored).
- Legacy posts accept `body` until explicit conversion (`POST .../document/convert`).

## Conversion

- Legacy → block: creates a `pre_layout_conversion` revision, then stores structured document.
- Published URLs, slugs, and metadata are unchanged.
- No mass conversion of existing posts.

## Image cleanup (v1)

- Removing or replacing an image block does **not** delete the stored media object.
- Images may remain referenced by revisions or other posts.
- Orphan cleanup is deferred to the platform media lifecycle (reference-aware / delayed).

## Frontend

- In `block_document` mode, only `content_document` is sent on autosave (not parallel `body`).
- Legacy markdown section toolbar is hidden when `block_document` mode is active.
