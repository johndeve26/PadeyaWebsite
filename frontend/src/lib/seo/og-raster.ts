/**
 * Raster helpers for next/og ImageResponse cards.
 * WhatsApp/iMessage reject SVG; broken remote URLs must not crash generation.
 */

import { readFile } from "node:fs/promises";
import path from "node:path";

import { brand } from "@/lib/brand";
import { resolvePublicAssetUrl } from "@/lib/seo/public-asset";

const MAX_BYTES = 8_000_000;

export function initialsFromName(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "P";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
}

/** Fetch a remote/absolute raster into a data URL for ImageResponse. */
export async function fetchRasterAsDataUrl(
  imageUrl: string | null | undefined,
): Promise<string | null> {
  const absolute = resolvePublicAssetUrl(imageUrl);
  if (!absolute) return null;
  try {
    const pathname = new URL(absolute).pathname.toLowerCase();
    if (pathname.endsWith(".svg") || pathname.includes(".svg/")) return null;

    const res = await fetch(absolute, {
      next: { revalidate: 3600 },
      headers: { Accept: "image/*,*/*;q=0.8" },
    });
    if (!res.ok) return null;
    const contentType = (res.headers.get("content-type") || "").toLowerCase();
    if (contentType.includes("svg")) return null;

    const bytes = await res.arrayBuffer();
    if (bytes.byteLength === 0 || bytes.byteLength > MAX_BYTES) return null;

    const mime = contentType.startsWith("image/")
      ? contentType.split(";")[0]!.trim()
      : "image/png";
    const b64 = Buffer.from(bytes).toString("base64");
    return `data:${mime};base64,${b64}`;
  } catch {
    return null;
  }
}

/** Load a file from `frontend/public` as a data URL (no runtime HTTP). */
export async function loadPublicAssetDataUrl(
  publicPath: string,
): Promise<string | null> {
  const rel = publicPath.replace(/^\//, "");
  try {
    const filePath = path.join(process.cwd(), "public", rel);
    const bytes = await readFile(filePath);
    if (!bytes.byteLength || bytes.byteLength > MAX_BYTES) return null;
    const ext = path.extname(rel).toLowerCase();
    const mime =
      ext === ".jpg" || ext === ".jpeg"
        ? "image/jpeg"
        : ext === ".webp"
          ? "image/webp"
          : "image/png";
    return `data:${mime};base64,${bytes.toString("base64")}`;
  } catch {
    return null;
  }
}

/** Dark-surface brand mark for OG cards. */
export async function loadBrandLogoDataUrl(): Promise<string | null> {
  return loadPublicAssetDataUrl(brand.logos.dark);
}
