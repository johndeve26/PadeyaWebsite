# SEO launch checklist (Phase 1C)

Post-deploy steps for production SEO on **https://padeya.com**. Indexing is **not** immediate after submission.

**Related:** [SEO_IMPLEMENTATION.md](./SEO_IMPLEMENTATION.md) · [SEO_AUDIT.md](./SEO_AUDIT.md) · [SEO.md](./SEO.md)

---

## Gate status (post-implementation audit — 2026-07-24)

| Gate | Status |
|------|--------|
| Code Phases 0A–1C | Present in workspace (~**88 / 100** code readiness) |
| Live production smoke | **FAILED** (~**54 / 100** live) |
| Launch recommendation | **not ready** — deploy phases, then re-run smoke |

Do **not** submit sitemaps or request indexing while smoke fails.

Observed live blockers (pre-deploy):

- robots.txt missing `/sponsor/`, `/connect/`, `/messages/`, checkout disallows
- sitemap still includes `/events/search`; **0** Host/Fan/Sponsor/event entity URLs
- soft-200 for missing event/merch/host
- home missing Organization/WebSite JSON-LD
- `/events/search` still self-canonical / not noindex on live

---

## Before requesting indexing

1. **Deploy** Phases 0A–1C to production (`APP_ENV=production`, `NEXT_PUBLIC_SITE_URL=https://padeya.com`).
2. Run the production smoke script and fix any failures:

```bash
cd frontend
SEO_BASE_URL=https://padeya.com npm run seo:production-smoke
# Optional stricter sample requirements:
# SEO_SMOKE_STRICT=1 SEO_BASE_URL=https://padeya.com npm run seo:production-smoke
```

3. Confirm local regression suite still passes:

```bash
cd frontend
npm run test:seo
npm run build
```

4. Confirm public entity inventory exists (at least one listed event, host, sponsor, merch) so sitemap is not hubs-only.

Do **not** request indexing until smoke passes against the live domain.

---

## Environment variables

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `GOOGLE_SITE_VERIFICATION` | Optional | Meta-tag Google Search Console verification token |
| `BING_SITE_VERIFICATION` | Optional | Bing Webmaster `msvalidate.01` token |
| `NEXT_PUBLIC_GA_MEASUREMENT_ID` | Optional | GA4 (`G-…`) — loads only in production **after** user Allow on `/cookies` |

`NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION` / `NEXT_PUBLIC_BING_SITE_VERIFICATION` are also accepted if the token must be available at build time.

**Preferred production verification:** DNS TXT (or HTML file upload) in Google Search Console / Bing Webmaster. Meta tokens are a fallback — never hardcode them in the repo.

---

## Google Search Console

1. Add a **URL-prefix** or **Domain** property for `https://padeya.com` (Domain + DNS TXT preferred).
2. Verify ownership (DNS preferred; or set `GOOGLE_SITE_VERIFICATION` and redeploy).
3. Submit sitemap: `https://padeya.com/sitemap.xml`.
4. URL Inspection — check at least:
   - Homepage `/`
   - One public event `/events/{slug}`
   - One host Legacy `/u/{username}`
   - One sponsor `/sponsors/{slug}`
   - One merch product `/merch/{slug}`
5. Request indexing **only** after production smoke passes and the inspect result looks healthy.
6. Monitor Coverage / Page indexing over days–weeks (not minutes).

---

## Bing Webmaster Tools (optional)

1. Verify with DNS or `BING_SITE_VERIFICATION`.
2. Submit the same sitemap URL.
3. Spot-check the same representative URLs.

---

## Analytics decision (do not skip)

| Layer | Behavior |
|-------|----------|
| **First-party** (`AnalyticsProvider` → `/analytics/track*`) | Always on for product operation. Uses localStorage/sessionStorage IDs. **Not** gated by GA consent. |
| **Optional GA4** | Off unless `NEXT_PUBLIC_GA_MEASUREMENT_ID` is set **and** production SEO environment **and** consent `granted` on `/cookies`. Denied / unset → GA4 never loads. Non-production → never loads. |

GA4 is **not** required for SEO launch. Keep first-party analytics as primary unless product needs GA4 reports.

Consent control: `/cookies` → `OptionalAnalyticsConsentControls` (only visible when GA is configured).

---

## Production smoke — what must pass

Against `SEO_BASE_URL` (default `https://padeya.com`):

| Check | Expectation |
|-------|-------------|
| `/robots.txt` | Allows public crawl; private disallows; `Sitemap: https://padeya.com/sitemap.xml` |
| `/sitemap.xml` | Parseable; only `https://padeya.com` URLs; no query/checkout/admin/private |
| Public hubs + samples | HTTP 200; title/description/canonical/OG/Twitter; expected JSON-LD types |
| Faceted `/events?…` | Canonical `/events` |
| Private routes | Auth redirect or protected response; noindex where applicable |
| Missing event/merch/sponsor/host | HTTP **404** (no soft-200) |
| Canonicals | https padeya.com; no localhost / Vercel / Render / smartlancedesigns |

Fail conditions: excessive redirect chains, forbidden hosts in sitemap/canonical, missing required entity samples when `SEO_SMOKE_STRICT=1`.

---

## Core Web Vitals / performance (manual)

Do **not** rely on synthetic Lighthouse in CI. After launch, check in **PageSpeed Insights** and Search Console CWV for:

| Page | Why |
|------|-----|
| `/` | Brand homepage LCP |
| `/events` | Discovery hub |
| `/events/{slug}` | Primary landing |
| `/u/{username}` | Host Legacy |
| `/sponsors/{slug}` | Sponsor profile |
| `/merch/{slug}` | Product detail |

Record **LCP**, **INP**, **CLS**. Fix regressions in product work — this checklist only ensures you measure them.

---

## Staging / preview safety (never index)

| Signal | Expectation |
|--------|-------------|
| Root robots / page robots | noindex |
| `/robots.txt` | `Disallow: /` |
| Middleware | `X-Robots-Tag: noindex` (where configured) |
| Sitemap advertisement | **No** production sitemap line in non-prod robots |

Do not submit staging URLs to Search Console as the primary property.

---

## After smoke passes

- [ ] GSC verified
- [ ] Sitemap submitted
- [ ] Representative URLs inspected
- [ ] Indexing requested (homepage + key entities) — expect delayed results
- [ ] Optional Bing done or explicitly skipped
- [ ] Optional GA4 configured **or** consciously left unset
- [ ] PSI/CWV spot-check noted
- [ ] `docs/EXECUTION_TRACKER.md` updated with the smoke run
