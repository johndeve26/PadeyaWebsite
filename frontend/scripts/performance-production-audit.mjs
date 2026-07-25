#!/usr/bin/env node
/**
 * Safe, low-volume production performance audit (GET/HEAD only).
 *
 * Timing terminology:
 * - total_response_ms — full fetch round-trip including body transfer (NOT TTFB)
 * - TTFB / DNS / TLS — use curl --write-out phase timings separately
 *   (see docs/performance-audit-curl-phases.json)
 *
 * Cold-start probe:
 * - Labeled NOT A TRUE IDLE COLD START unless the service was idle long enough
 *   for the platform to sleep. Short gaps only compare first vs subsequent.
 *
 * Usage:
 *   PERF_BASE_URL=https://padeya.com node frontend/scripts/performance-production-audit.mjs
 *   PERF_API_URL=https://padeyawebsite.onrender.com node ...
 *
 * Does NOT: login, mutate data, create orders/tickets, stress test, or load test.
 */

import { writeFileSync } from "node:fs";
import { resolve } from "node:path";

const FE = (process.env.PERF_BASE_URL || "https://padeya.com").replace(/\/$/, "");
const API = (
  process.env.PERF_API_URL || "https://padeyawebsite.onrender.com"
).replace(/\/$/, "");
const SAMPLES = Math.min(Number(process.env.PERF_SAMPLES || 3), 5);
const OUT =
  process.env.PERF_OUT ||
  resolve(process.cwd(), "docs/performance-audit-timings.json");

const FE_ROUTES = [
  "/",
  "/events",
  "/events/demo-afrobeats-night-live",
  "/hosts",
  "/u/mainlandvibes",
  "/fans",
  "/f/pizzlecole",
  "/sponsorships",
  "/sponsors/korawave-pay",
  "/merch",
  "/merch/mainland-vibes-logo-tee",
  "/blog",
  "/help",
  "/login",
  "/register",
  "/dashboard",
  "/host",
  "/sponsor",
];

const API_ROUTES = [
  "/health",
  "/ready",
  "/api/v1/events",
  "/api/v1/events/demo-afrobeats-night-live",
  "/api/v1/legacy/mainlandvibes",
  "/api/v1/u/mainlandvibes/legacy",
  "/api/v1/f/pizzlecole",
  "/api/v1/sponsors/public/korawave-pay",
  "/api/v1/merch?limit=50&sort=newest",
  "/api/v1/merch/mainland-vibes-logo-tee",
  "/api/v1/blog/posts?limit=20",
  "/api/v1/help/articles?limit=20",
];

function median(nums) {
  if (!nums.length) return null;
  const s = [...nums].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

async function timeFetch(url, { method = "GET", headers = {} } = {}) {
  const t0 = performance.now();
  let res;
  try {
    res = await fetch(url, {
      method,
      headers: {
        Accept: "text/html,application/json,*/*",
        "User-Agent": "PadeyaPerformanceAudit/1.0 (+safe-get-only)",
        ...headers,
      },
      redirect: "manual",
      cache: "no-store",
    });
  } catch (err) {
    const total_response_ms = performance.now() - t0;
    return {
      ok: false,
      error: String(err?.message || err),
      total_response_ms,
      // legacy alias — do not treat as TTFB
      total_ms: total_response_ms,
    };
  }
  const buf = Buffer.from(await res.arrayBuffer());
  const total_response_ms = performance.now() - t0;
  const h = Object.fromEntries(res.headers.entries());
  return {
    ok: true,
    status: res.status,
    total_response_ms,
    total_ms: total_response_ms,
    bytes: buf.byteLength,
    redirect: [301, 302, 303, 307, 308].includes(res.status)
      ? h.location || true
      : null,
    headers: {
      cache_control: h["cache-control"] || null,
      content_encoding: h["content-encoding"] || null,
      content_type: h["content-type"] || null,
      etag: h.etag || null,
      age: h.age || null,
      server_timing: h["server-timing"] || null,
      x_request_id: h["x-request-id"] || null,
      x_vercel_cache: h["x-vercel-cache"] || null,
      x_vercel_id: h["x-vercel-id"] || null,
      cf_cache_status: h["cf-cache-status"] || null,
      vary: h.vary || null,
    },
  };
}

async function sampleUrl(label, url, samples) {
  const runs = [];
  for (let i = 0; i < samples; i++) {
    const r = await timeFetch(url);
    runs.push(r);
    await new Promise((r) => setTimeout(r, 350));
  }
  const ok = runs.filter((r) => r.ok);
  const times = ok.map((r) => r.total_response_ms);
  const statuses = ok.map((r) => r.status);
  return {
    label,
    url,
    samples: runs.length,
    metric: "total_response_ms",
    metric_note:
      "Full response/body transfer time. NOT TTFB — use curl phase timings for TTFB.",
    median_total_response_ms: median(times),
    // legacy fields for older consumers
    median_ms: median(times),
    min_ms: times.length ? Math.min(...times) : null,
    max_ms: times.length ? Math.max(...times) : null,
    first_total_response_ms: times[0] ?? null,
    first_ms: times[0] ?? null,
    warm_median_total_response_ms:
      times.length > 1 ? median(times.slice(1)) : null,
    warm_median_ms: times.length > 1 ? median(times.slice(1)) : null,
    statuses,
    bytes_median: median(ok.map((r) => r.bytes).filter((n) => n != null)),
    last_headers: ok.at(-1)?.headers || null,
    errors: runs.filter((r) => !r.ok).map((r) => r.error),
    runs,
  };
}

async function main() {
  const started = new Date().toISOString();
  console.log(`Pàdéyá production audit @ ${started}`);
  console.log(`FE=${FE} API=${API} samples=${SAMPLES}`);
  console.log(
    "Metric: total_response_ms (full transfer). TTFB requires curl phase timings.",
  );

  const frontend = [];
  for (const path of FE_ROUTES) {
    const row = await sampleUrl(`FE ${path}`, `${FE}${path}`, SAMPLES);
    console.log(
      `  ${path.padEnd(40)} total_response_ms med=${row.median_total_response_ms?.toFixed(0)} status=${row.statuses.join(",")} bytes=${row.bytes_median}`,
    );
    frontend.push(row);
  }

  await new Promise((r) => setTimeout(r, 800));

  const api = [];
  for (const path of API_ROUTES) {
    const row = await sampleUrl(`API ${path}`, `${API}${path}`, SAMPLES);
    console.log(
      `  ${path.padEnd(50)} total_response_ms med=${row.median_total_response_ms?.toFixed(0)} status=${row.statuses.join(",")} bytes=${row.bytes_median}`,
    );
    api.push(row);
  }

  const coldProbe = {
    label: "NOT A TRUE IDLE COLD START",
    note:
      "NOT A TRUE IDLE COLD START unless the Render service was idle long enough to sleep. This probe only compares first vs immediate subsequent requests after a short gap.",
    health: await sampleUrl("cold-health", `${API}/health`, 2),
    ready: await sampleUrl("cold-ready", `${API}/ready`, 2),
    events: await sampleUrl("cold-events", `${API}/api/v1/events`, 2),
  };

  const report = {
    brand: "Pàdéyá",
    started,
    finished: new Date().toISOString(),
    fe_base: FE,
    api_base: API,
    samples_per_route: SAMPLES,
    timing_definitions: {
      total_response_ms:
        "Full fetch round-trip including body download. Not TTFB.",
      ttfb:
        "Use curl --write-out time_starttransfer (see docs/performance-audit-curl-phases.json).",
    },
    frontend,
    api,
    coldProbe,
  };

  writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(`\nWrote ${OUT}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
