/**
 * Phase 10 — critical frontend API path inventory + OpenAPI contract check.
 * Static analysis only (no browser). Does not print secrets.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FE = path.resolve(__dirname, "..");
const LIB = path.join(FE, "src/lib");
const LIVE = "https://padeyawebsite.onrender.com/openapi.json";

const CRITICAL = [
  { method: "POST", path: "/api/v1/auth/register", file: "api.ts / auth pages" },
  { method: "POST", path: "/api/v1/auth/login", file: "api.ts / auth pages" },
  { method: "POST", path: "/api/v1/auth/refresh", file: "api.ts" },
  { method: "POST", path: "/api/v1/auth/logout", file: "api.ts" },
  { method: "POST", path: "/api/v1/orders", file: "commerce-api.ts" },
  { method: "POST", path: "/api/v1/orders/{order_id}/cancel", file: "commerce-api.ts" },
  { method: "POST", path: "/api/v1/payments/checkout/{order_id}", file: "commerce-api.ts" },
  { method: "POST", path: "/api/v1/payments/checkout/{order_id}/confirm", file: "commerce-api.ts" },
  { method: "GET", path: "/api/v1/tickets/mine", file: "commerce-api.ts" },
  { method: "POST", path: "/api/v1/admin/sponsorship-invoices/{invoice_id}/void", file: "sponsor-deals-api.ts" },
  { method: "POST", path: "/api/v1/memories/events/{event_id}/photos", file: "memories-api.ts" },
  { method: "GET", path: "/api/v1/admin/emails/settings", file: "email-api.ts", hidden: true },
  { method: "POST", path: "/api/v1/admin/users/{user_id}/impersonation/start", file: "api.ts" },
];

function walk(dir, out = []) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(p, out);
    else if (/\.(ts|tsx|mjs|js)$/.test(ent.name)) out.push(p);
  }
  return out;
}

function extractCalls(src) {
  const calls = [];
  const re =
    /(?:apiRequest|apiUpload|apiDownload)\s*(?:<[^>]+>)?\s*\(\s*[`'"](\/[^`'"]+)/g;
  let m;
  while ((m = re.exec(src))) {
    calls.push(m[1].split("?")[0].replace(/\$\{[^}]+\}/g, "{id}"));
  }
  // template with /orders/${orderId}/cancel
  const re2 = /`(\/[^`$]*\$\{[^}]+\}[^`]*)`/g;
  while ((m = re2.exec(src))) {
    const norm = m[1]
      .replace(/\$\{[^}]+\}/g, "{id}")
      .split("?")[0];
    if (norm.startsWith("/")) calls.push(norm);
  }
  return calls;
}

const files = walk(LIB);
const inventory = [];
for (const file of files) {
  const src = fs.readFileSync(file, "utf8");
  const rel = path.relative(FE, file);
  for (const p of extractCalls(src)) {
    inventory.push({ file: rel, path: p.startsWith("/api/") ? p : `/api/v1${p}` });
  }
}

const openapi = await (await fetch(LIVE, { headers: { "User-Agent": "PadeyaPhase10" } })).json();
const liveOps = new Set();
for (const [p, methods] of Object.entries(openapi.paths || {})) {
  for (const method of Object.keys(methods)) {
    if (method.startsWith("x-") || method === "parameters") continue;
    liveOps.add(`${method.toUpperCase()} ${p}`);
  }
}

function normalizeFePath(p) {
  // FE often uses /orders/{id} while OpenAPI uses /api/v1/orders/{order_id}
  let x = p;
  if (!x.startsWith("/api/v1")) x = `/api/v1${x.startsWith("/") ? x : `/${x}`}`;
  return x
    .replace(/\{id\}/g, "{order_id}")
    .replace(/\{invoiceId\}/g, "{invoice_id}")
    .replace(/\{eventId\}/g, "{event_id}")
    .replace(/\{userId\}/g, "{user_id}")
    .replace(/\{ticketId\}/g, "{ticket_id}");
}

const diff = [];
for (const c of CRITICAL) {
  const keyGet = `GET ${c.path}`;
  const keyPost = `POST ${c.path}`;
  const key = `${c.method} ${c.path}`;
  let classification = "PATH_MISMATCH";
  if (c.hidden) {
    classification = "HIDDEN_ROUTE_MATCHED";
  } else if (liveOps.has(key)) {
    classification = "MATCHED";
  } else {
    // try fuzzy: replace param names
    const fuzzy = [...liveOps].find((op) => {
      const [m, p] = op.split(" ");
      if (m !== c.method) return false;
      const a = p.replace(/\{[^}]+\}/g, "{}");
      const b = c.path.replace(/\{[^}]+\}/g, "{}");
      return a === b;
    });
    classification = fuzzy ? "MATCHED" : "PATH_MISMATCH";
  }
  diff.push({ ...c, classification, in_live_openapi: liveOps.has(key) || classification === "MATCHED" });
}

const cancelInFe = inventory.some((i) => i.path.includes("/orders/") && i.path.includes("/cancel"));
const doublePrefix = inventory.filter((i) => i.path.includes("/api/v1/api/v1"));

console.log(
  JSON.stringify(
    {
      ok: !doublePrefix.length && cancelInFe,
      critical: diff,
      cancel_buyer_order_in_frontend: cancelInFe,
      double_prefix_count: doublePrefix.length,
      inventory_sample_count: inventory.length,
      live_ops: liveOps.size,
    },
    null,
    2,
  ),
);

if (!cancelInFe) {
  console.error("FAIL: cancelBuyerOrder path missing from frontend inventory");
  process.exit(1);
}
if (doublePrefix.length) {
  console.error("FAIL: double /api/v1 prefix detected");
  process.exit(1);
}
