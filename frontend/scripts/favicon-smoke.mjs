/**
 * Favicon / Google Search icon smoke checks.
 * Run: node scripts/favicon-smoke.mjs
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function exists(rel) {
  return fs.existsSync(path.join(root, rel));
}

function readBytes(rel) {
  return fs.readFileSync(path.join(root, rel));
}

/** Read width/height from a PNG IHDR chunk. */
function pngSize(buf) {
  assert.ok(buf.length >= 24, "PNG too short");
  assert.equal(buf.subarray(0, 8).toString("hex"), "89504e470d0a1a0a", "not a PNG");
  const width = buf.readUInt32BE(16);
  const height = buf.readUInt32BE(20);
  return { width, height };
}

// --- Required brand favicon assets ---
assert.ok(exists("src/app/favicon.ico"), "app/favicon.ico missing");
assert.ok(exists("public/icons/icon-48.png"), "icon-48.png missing (Google ≥48px)");
assert.ok(exists("public/icons/icon-192.png"), "icon-192.png missing");
assert.ok(exists("public/icons/icon-512.png"), "icon-512.png missing");
assert.ok(exists("public/icons/apple-touch-icon.png"), "apple-touch-icon.png missing");

// No legacy public favicon that could conflict with app/favicon.ico
assert.equal(
  exists("public/favicon.ico"),
  false,
  "public/favicon.ico must not conflict with app/favicon.ico",
);
assert.equal(exists("src/app/icon.png"), false, "app/icon.png would duplicate metadata.icons");
assert.equal(exists("src/app/icon.svg"), false, "app/icon.svg would duplicate metadata.icons");
assert.equal(
  exists("src/app/apple-icon.png"),
  false,
  "use metadata apple → /icons/apple-touch-icon.png",
);

// --- icon-48 must be square ≥48 ---
const icon48Bytes = readBytes("public/icons/icon-48.png");
const size48 = pngSize(icon48Bytes);
assert.equal(size48.width, size48.height, "icon-48 must be square");
assert.ok(size48.width >= 48, `icon-48 must be ≥48px, got ${size48.width}`);
assert.ok(icon48Bytes.length > 800, "icon-48 looks empty/legacy");

const icon192 = pngSize(readBytes("public/icons/icon-192.png"));
assert.equal(icon192.width, icon192.height, "icon-192 must be square");
assert.equal(icon192.width, 192);

const icon512 = pngSize(readBytes("public/icons/icon-512.png"));
assert.equal(icon512.width, icon512.height, "icon-512 must be square");
assert.equal(icon512.width, 512);

const apple = pngSize(readBytes("public/icons/apple-touch-icon.png"));
assert.equal(apple.width, apple.height, "apple-touch-icon must be square");
assert.equal(apple.width, 180);

// --- favicon.ico multi-size brand ICO (PNG entries) ---
const ico = readBytes("src/app/favicon.ico");
assert.ok(ico.length > 1000, "favicon.ico suspiciously small");
const icoCount = ico.readUInt16LE(4);
assert.ok(icoCount >= 2, `favicon.ico should include multiple sizes, got ${icoCount}`);
const icoSizes = [];
for (let i = 0; i < icoCount; i++) {
  const entryOff = 6 + i * 16;
  const w = ico[entryOff] || 256;
  const h = ico[entryOff + 1] || 256;
  const byteSize = ico.readUInt32LE(entryOff + 8);
  const imgOff = ico.readUInt32LE(entryOff + 12);
  assert.equal(w, h, `ICO entry ${i} must be square`);
  icoSizes.push(w);
  const magic = ico.subarray(imgOff, imgOff + 8);
  assert.ok(
    magic[0] === 0x89 && magic.toString("ascii", 1, 4) === "PNG",
    `ICO entry ${i} must be PNG-compressed`,
  );
  assert.ok(byteSize > 100, `ICO entry ${i} too small`);
}
assert.ok(icoSizes.includes(48), `favicon.ico must include 48x48, got ${icoSizes.join(",")}`);
assert.ok(icoSizes.includes(32), `favicon.ico must include 32x32, got ${icoSizes.join(",")}`);

// --- layout metadata: single authoritative icon set ---
const layout = read("src/app/layout.tsx");
assert.match(layout, /icons:\s*\{/);
assert.match(layout, /\/icons\/icon-48\.png/);
assert.match(layout, /sizes:\s*"48x48"/);
assert.match(layout, /\/icons\/icon-192\.png/);
assert.match(layout, /\/icons\/icon-512\.png/);
assert.match(layout, /\/icons\/apple-touch-icon\.png/);
assert.doesNotMatch(
  layout,
  /url:\s*["']\/favicon\.ico/,
  "do not duplicate favicon.ico in metadata.icons (App Router file serves it)",
);
assert.doesNotMatch(layout, /shortcut icon/i);
assert.doesNotMatch(layout, /high-?heel|shoe/i);

// --- No WordPress / old shoe asset references in frontend source ---
const scanRoots = ["src", "public"];
const forbiddenName = /shoe|high-?heel|wp-content|site\.webmanifest|wordpress/i;
const forbiddenText = /wp-content\/uploads|wp-includes|site\.webmanifest/i;
for (const dir of scanRoots) {
  const abs = path.join(root, dir);
  /** @type {string[]} */
  const stack = [abs];
  while (stack.length) {
    const cur = stack.pop();
    for (const ent of fs.readdirSync(cur, { withFileTypes: true })) {
      if (ent.name === "node_modules" || ent.name === ".next") continue;
      const full = path.join(cur, ent.name);
      if (ent.isDirectory()) {
        stack.push(full);
        continue;
      }
      assert.doesNotMatch(ent.name, forbiddenName, `forbidden legacy name: ${full}`);
      if (!/\.(tsx?|jsx?|mjs|json|webmanifest|html|css|md|svg)$/i.test(ent.name)) continue;
      const text = fs.readFileSync(full, "utf8");
      assert.doesNotMatch(
        text,
        forbiddenText,
        `forbidden legacy reference in ${path.relative(root, full)}`,
      );
    }
  }
}

// Legacy WP register path must permanently redirect to /register (central map)
const nextConfig = read("next.config.ts");
const legacyMap = read("src/lib/seo/legacy-redirects.ts");
assert.match(nextConfig, /buildAppRedirects/);
assert.match(legacyMap, /member-register/);
assert.match(legacyMap, /destination:\s*["']\/register["']/);
assert.match(legacyMap, /www\.padeya\.com|WWW_HOST/);
assert.match(legacyMap, /LIVE_SITE_ORIGIN|https:\/\/padeya\.com/);

// robots must not block favicons / icons
const robots = read("src/app/robots.ts");
assert.doesNotMatch(robots, /Disallow:\s*\/favicon/i);
assert.doesNotMatch(robots, /Disallow:\s*\/icons/i);
assert.doesNotMatch(robots, /["']\/favicon/);
assert.doesNotMatch(robots, /["']\/icons/);

// PWA manifest still points at brand icons (unchanged purpose)
const manifest = JSON.parse(read("public/manifest.webmanifest"));
for (const icon of manifest.icons) {
  assert.match(icon.src, /^\/icons\/icon-(192|512)\.png$/);
  assert.ok(exists(`public${icon.src}`));
}

console.log("favicon-smoke: ok");
console.log(`  ✓ icon-48 ${size48.width}x${size48.height}`);
console.log(`  ✓ favicon.ico sizes ${icoSizes.join(", ")}`);
console.log("  ✓ layout metadata icons (48/192/512 + apple)");
console.log("  ✓ no conflicting app/icon.* / public/favicon.ico");
console.log("  ✓ www→apex + member-register→/register redirects present");
console.log("  ✓ robots allow favicon/icons");
