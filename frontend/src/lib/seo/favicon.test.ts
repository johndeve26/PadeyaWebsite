import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const root = path.join(__dirname, "../../..");

function read(rel: string) {
  return fs.readFileSync(path.join(root, rel));
}

function pngSize(buf: Buffer) {
  const width = buf.readUInt32BE(16);
  const height = buf.readUInt32BE(20);
  return { width, height };
}

describe("favicon / Google Search icon configuration", () => {
  it("exposes a square ≥48px stable brand PNG", () => {
    const buf = read("public/icons/icon-48.png");
    const { width, height } = pngSize(buf);
    expect(width).toBe(height);
    expect(width).toBeGreaterThanOrEqual(48);
  });

  it("ships a multi-size brand favicon.ico with a 48px entry", () => {
    const ico = read("src/app/favicon.ico");
    const count = ico.readUInt16LE(4);
    expect(count).toBeGreaterThanOrEqual(2);
    const sizes: number[] = [];
    for (let i = 0; i < count; i++) {
      const off = 6 + i * 16;
      sizes.push(ico[off] || 256);
    }
    expect(sizes).toContain(48);
    expect(sizes).toContain(32);
  });

  it("declares one authoritative icons set in root layout (no favicon.ico duplicate)", () => {
    const layout = fs.readFileSync(path.join(root, "src/app/layout.tsx"), "utf8");
    expect(layout).toMatch(/\/icons\/icon-48\.png/);
    expect(layout).toMatch(/sizes:\s*"48x48"/);
    expect(layout).not.toMatch(/url:\s*["']\/favicon\.ico/);
    expect(layout).not.toMatch(/shortcut icon/i);
  });

  it("does not keep a conflicting public/favicon.ico or app/icon.* file", () => {
    expect(fs.existsSync(path.join(root, "public/favicon.ico"))).toBe(false);
    expect(fs.existsSync(path.join(root, "src/app/icon.png"))).toBe(false);
    expect(fs.existsSync(path.join(root, "src/app/icon.svg"))).toBe(false);
    expect(fs.existsSync(path.join(root, "src/app/apple-icon.png"))).toBe(false);
  });

  it("keeps www→apex and legacy member-register redirects", () => {
    const cfg = fs.readFileSync(path.join(root, "next.config.ts"), "utf8");
    const map = fs.readFileSync(
      path.join(root, "src/lib/seo/legacy-redirects.ts"),
      "utf8",
    );
    expect(cfg).toMatch(/buildAppRedirects/);
    expect(map).toMatch(/www\.padeya\.com|WWW_HOST/);
    expect(map).toMatch(/LIVE_SITE_ORIGIN|padeya\.com\/:path\*/);
    expect(map).toMatch(/member-register/);
    expect(map).toMatch(/destination:\s*["']\/register["']/);
  });
});
