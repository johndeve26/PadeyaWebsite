/**
 * Raster helpers for next/og ImageResponse cards.
 * WhatsApp/iMessage reject SVG; @vercel/og (Satori/resvg) rejects WebP/AVIF —
 * convert those to PNG. Broken remote URLs must not crash generation.
 */

import { readFile } from "node:fs/promises";
import path from "node:path";

import { brand } from "@/lib/brand";
import { resolvePublicAssetUrl } from "@/lib/seo/public-asset";
import { absoluteUrl } from "@/lib/seo/site";

const MAX_BYTES = 8_000_000;

/** Formats Satori/resvg cannot decode into ImageResponse. */
const NEEDS_PNG_REENCODE = /image\/(webp|avif|heic|heif)/i;

export function initialsFromName(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "P";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
}

async function toPngDataUrl(bytes: ArrayBuffer): Promise<string | null> {
  try {
    const sharp = (await import("sharp")).default;
    const png = await sharp(Buffer.from(bytes))
      .rotate()
      .resize({
        width: 1200,
        height: 1200,
        fit: "inside",
        withoutEnlargement: true,
      })
      .png({ compressionLevel: 8 })
      .toBuffer();
    if (!png.byteLength || png.byteLength > MAX_BYTES) return null;
    return `data:image/png;base64,${png.toString("base64")}`;
  } catch {
    return null;
  }
}

function looksLikeWebpPath(url: string): boolean {
  try {
    const pathname = new URL(url).pathname.toLowerCase();
    return pathname.endsWith(".webp") || pathname.endsWith(".avif");
  } catch {
    return /\.webp($|\?)/i.test(url) || /\.avif($|\?)/i.test(url);
  }
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

    const needsReencode =
      NEEDS_PNG_REENCODE.test(contentType) || looksLikeWebpPath(absolute);
    if (needsReencode) {
      return toPngDataUrl(bytes);
    }

    const mime = contentType.startsWith("image/")
      ? contentType.split(";")[0]!.trim()
      : "image/png";
    // JPEG/PNG/GIF — pass through. Still clamp huge rasters via sharp when big.
    if (bytes.byteLength > 1_500_000) {
      return toPngDataUrl(bytes);
    }
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
    if (mime === "image/webp") {
      return toPngDataUrl(bytes.buffer.slice(
        bytes.byteOffset,
        bytes.byteOffset + bytes.byteLength,
      ));
    }
    return `data:${mime};base64,${bytes.toString("base64")}`;
  } catch {
    // Vercel serverless may omit public/ from the function FS — fall back to HTTP.
    return fetchRasterAsDataUrl(absoluteUrl(`/${rel}`));
  }
}

/** Dark-surface brand mark for OG cards. */
export async function loadBrandLogoDataUrl(): Promise<string | null> {
  return loadPublicAssetDataUrl(brand.logos.dark);
}
