/** Tiny unit check for login redirect sanitizer logic (mirrors safe-next.ts). */
import assert from "node:assert/strict";

function safeNextPath(raw, fallback = "/dashboard") {
  if (!raw) return fallback;
  const value = raw.trim();
  if (!value.startsWith("/")) return fallback;
  if (value.startsWith("//")) return fallback;
  if (value.includes("://")) return fallback;
  return value;
}

assert.equal(safeNextPath(null), "/dashboard");
assert.equal(safeNextPath("/host/events"), "/host/events");
assert.equal(safeNextPath("//evil.com"), "/dashboard");
assert.equal(safeNextPath("https://evil.com"), "/dashboard");
assert.equal(safeNextPath("/admin?x=1"), "/admin?x=1");
console.log("safe-next smoke passed");
