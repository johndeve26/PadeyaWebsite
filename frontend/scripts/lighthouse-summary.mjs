#!/usr/bin/env node
/**
 * Summarize one or more Lighthouse JSON reports for Pàdéyá CWV comparisons.
 *
 * Usage:
 *   node frontend/scripts/lighthouse-summary.mjs docs/lighthouse-phase3/*.json
 *   node frontend/scripts/lighthouse-summary.mjs path/to/report.json --json
 */

import { readFileSync } from "node:fs";
import path from "node:path";

function num(audits, id) {
  const v = audits?.[id]?.numericValue;
  return typeof v === "number" ? v : null;
}

function round(v, digits = 0) {
  if (v == null || Number.isNaN(v)) return null;
  const f = 10 ** digits;
  return Math.round(v * f) / f;
}

function transferByType(audits, type) {
  const items = audits?.["network-requests"]?.details?.items || [];
  return items
    .filter((i) => i.resourceType === type)
    .reduce((sum, i) => sum + (i.transferSize || 0), 0);
}

function lcpElement(audits) {
  const items =
    audits?.["largest-contentful-paint-element"]?.details?.items || [];
  if (!items.length) return null;
  const node = items[0].node || items[0];
  if (!node || typeof node !== "object") return null;
  return {
    selector: node.selector || null,
    snippet: (node.snippet || "").slice(0, 160) || null,
    nodeLabel: node.nodeLabel || null,
  };
}

function clsCulprits(audits) {
  const shifts = audits?.["layout-shifts"]?.details?.items || [];
  return shifts.map((it) => {
    const node = it.node || {};
    const causes = (it.subItems?.items || []).map((sub) => ({
      cause: sub.cause || null,
      selector: sub.extra?.selector || null,
      snippet: (sub.extra?.snippet || "").slice(0, 140) || null,
    }));
    return {
      score: it.score ?? null,
      selector: node.selector || null,
      snippet: (node.snippet || "").slice(0, 140) || null,
      causes,
    };
  });
}

function lcpPhases(audits) {
  const insight = audits?.["lcp-breakdown-insight"]?.details?.items || [];
  const table = insight.find((i) => i.type === "table");
  const rows = table?.items || [];
  return rows.map((r) => ({
    subpart: r.subpart || r.label || null,
    duration_ms: round(r.duration, 1),
  }));
}

function summarizeFile(filePath) {
  const raw = JSON.parse(readFileSync(filePath, "utf8"));
  const audits = raw.audits || {};
  const perf = raw.categories?.performance?.score;
  const net = audits["network-requests"]?.details?.items || [];
  return {
    file: path.basename(filePath),
    requestedUrl: raw.requestedUrl || raw.finalUrl || null,
    performance: perf == null ? null : round(perf * 100),
    fcp_ms: round(num(audits, "first-contentful-paint")),
    lcp_ms: round(num(audits, "largest-contentful-paint")),
    cls: round(num(audits, "cumulative-layout-shift"), 3),
    tbt_ms: round(num(audits, "total-blocking-time")),
    speed_index_ms: round(num(audits, "speed-index")),
    total_transfer_bytes: net.reduce((s, i) => s + (i.transferSize || 0), 0),
    js_transfer_bytes: transferByType(audits, "Script"),
    image_transfer_bytes: transferByType(audits, "Image"),
    css_transfer_bytes: transferByType(audits, "Stylesheet"),
    lcp_element: lcpElement(audits),
    lcp_phases: lcpPhases(audits),
    cls_culprits: clsCulprits(audits),
  };
}

function median(values) {
  const xs = values.filter((v) => typeof v === "number").sort((a, b) => a - b);
  if (!xs.length) return null;
  const mid = Math.floor(xs.length / 2);
  return xs.length % 2 ? xs[mid] : (xs[mid - 1] + xs[mid]) / 2;
}

function main() {
  const args = process.argv.slice(2).filter((a) => a !== "--json");
  const asJson = process.argv.includes("--json");
  if (!args.length) {
    console.error(
      "Usage: node frontend/scripts/lighthouse-summary.mjs <report.json> [...]",
    );
    process.exit(1);
  }

  const rows = args.map(summarizeFile);
  if (asJson) {
    console.log(JSON.stringify({ reports: rows }, null, 2));
    return;
  }

  for (const r of rows) {
    console.log(`\n=== ${r.file} ===`);
    console.log(`URL: ${r.requestedUrl}`);
    console.log(
      `Perf ${r.performance} | FCP ${r.fcp_ms}ms | LCP ${r.lcp_ms}ms | CLS ${r.cls} | TBT ${r.tbt_ms}ms | SI ${r.speed_index_ms}ms`,
    );
    console.log(
      `Transfer total=${r.total_transfer_bytes} js=${r.js_transfer_bytes} img=${r.image_transfer_bytes} css=${r.css_transfer_bytes}`,
    );
    if (r.lcp_element) {
      console.log(
        `LCP element: ${r.lcp_element.selector || ""} ${r.lcp_element.nodeLabel || ""}`,
      );
    }
    if (r.lcp_phases?.length) {
      console.log(
        "LCP phases:",
        r.lcp_phases.map((p) => `${p.subpart}=${p.duration_ms}ms`).join(", "),
      );
    }
    if (r.cls_culprits?.length) {
      for (const c of r.cls_culprits) {
        console.log(`CLS culprit score=${c.score}: ${c.selector || ""}`);
        for (const cause of c.causes || []) {
          console.log(`  cause=${cause.cause} ${cause.selector || ""}`);
        }
      }
    }
  }

  const byRoute = new Map();
  for (const r of rows) {
    const key = r.requestedUrl || r.file;
    if (!byRoute.has(key)) byRoute.set(key, []);
    byRoute.get(key).push(r);
  }
  console.log("\n=== Medians by URL ===");
  for (const [url, list] of byRoute) {
    console.log(
      `${url}\n  n=${list.length} perf=${median(list.map((x) => x.performance))} LCP=${median(list.map((x) => x.lcp_ms))} CLS=${median(list.map((x) => x.cls))} TBT=${median(list.map((x) => x.tbt_ms))}`,
    );
  }
}

main();
