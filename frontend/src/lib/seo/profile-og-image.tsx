/**
 * Profile share cards — image-first DP showcase (1200×630).
 *
 * WhatsApp/iMessage need a bounded raster; the composed “passport badge”
 * layout felt mild. Prefer a full-bleed avatar with a light bottom identity
 * strip so the photo remains the hero.
 */

import { ImageResponse } from "next/og";

import { brand } from "@/lib/brand";
import { resolvePublicAssetUrl } from "@/lib/seo/public-asset";
import { PROFILE_OG_SIZE } from "@/lib/seo/profile-og-size";

export { PROFILE_OG_CONTENT_TYPE, PROFILE_OG_SIZE } from "@/lib/seo/profile-og-size";

async function avatarDataUrl(
  avatarUrl: string | null | undefined,
): Promise<string | null> {
  const absolute = resolvePublicAssetUrl(avatarUrl);
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
    if (bytes.byteLength === 0 || bytes.byteLength > 8_000_000) return null;

    const mime = contentType.startsWith("image/")
      ? contentType.split(";")[0]!.trim()
      : "image/png";
    const b64 = Buffer.from(bytes).toString("base64");
    return `data:${mime};base64,${b64}`;
  } catch {
    return null;
  }
}

function initialsFromName(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "P";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
}

export async function buildProfileOgImage(opts: {
  displayName: string;
  subtitle: string;
  avatarUrl?: string | null;
}): Promise<ImageResponse> {
  const name = opts.displayName.trim() || brand.name;
  const subtitle = opts.subtitle.trim();
  const avatar = await avatarDataUrl(opts.avatarUrl);
  const initials = initialsFromName(name);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          position: "relative",
          backgroundColor: brand.colors.ink,
          color: brand.colors.paper,
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
          overflow: "hidden",
        }}
      >
        {/* Full-bleed DP — the share card’s main signal */}
        {avatar ? (
          // eslint-disable-next-line @next/next/no-img-element -- ImageResponse
          <img
            src={avatar}
            width={PROFILE_OG_SIZE.width}
            height={PROFILE_OG_SIZE.height}
            alt=""
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: PROFILE_OG_SIZE.width,
              height: PROFILE_OG_SIZE.height,
              objectFit: "cover",
              objectPosition: "center",
            }}
          />
        ) : (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              backgroundImage:
                "radial-gradient(circle at 30% 20%, #222222 0%, #000000 70%)",
              fontSize: 180,
              fontWeight: 800,
              color: brand.colors.green,
            }}
          >
            {initials}
          </div>
        )}

        {/* Soft bottom grade so identity stays readable on any photo */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            height: 220,
            display: "flex",
            backgroundImage:
              "linear-gradient(to top, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.45) 55%, rgba(0,0,0,0) 100%)",
          }}
        />

        <div
          style={{
            position: "absolute",
            left: 56,
            right: 56,
            bottom: 44,
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-start",
          }}
        >
          <div
            style={{
              display: "flex",
              fontSize: 18,
              fontWeight: 800,
              letterSpacing: 5,
              textTransform: "uppercase",
              color: brand.colors.green,
              marginBottom: 10,
            }}
          >
            {brand.name}
            {subtitle ? ` · ${subtitle}` : ""}
          </div>
          <div
            style={{
              display: "flex",
              fontSize: 58,
              fontWeight: 800,
              letterSpacing: -1.2,
              lineHeight: 1.05,
              maxWidth: 1080,
              textShadow: "0 2px 18px rgba(0,0,0,0.55)",
            }}
          >
            {name.slice(0, 48)}
          </div>
        </div>

        {/* Accent bar */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: 10,
            backgroundColor: brand.colors.green,
          }}
        />
      </div>
    ),
    {
      ...PROFILE_OG_SIZE,
      headers: {
        "Cache-Control": "public, max-age=3600, s-maxage=3600",
      },
    },
  );
}
