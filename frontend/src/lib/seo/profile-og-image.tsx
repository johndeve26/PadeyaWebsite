/**
 * Profile share cards — always render the user DP (avatar) into a
 * crawler-safe 1200×630 raster so WhatsApp/iMessage do not fall back
 * to the brand logo when the raw avatar is oversized or SVG.
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
      // Avatars change rarely; keep OG generation snappy across crawlers.
      next: { revalidate: 3600 },
      headers: { Accept: "image/*,*/*;q=0.8" },
    });
    if (!res.ok) return null;
    const contentType = (res.headers.get("content-type") || "").toLowerCase();
    if (contentType.includes("svg")) return null;

    const bytes = await res.arrayBuffer();
    // Guard runaway downloads — raw avatars can be multi‑MB.
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
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: brand.colors.ink,
          backgroundImage:
            "radial-gradient(circle at 20% 20%, #1a1a1a 0%, #000000 55%)",
          color: brand.colors.paper,
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 280,
            height: 280,
            borderRadius: 9999,
            overflow: "hidden",
            border: `6px solid ${brand.colors.green}`,
            backgroundColor: brand.colors.surfaceDark,
          }}
        >
          {avatar ? (
            // eslint-disable-next-line @next/next/no-img-element -- ImageResponse
            <img
              src={avatar}
              width={280}
              height={280}
              alt=""
              style={{
                width: 280,
                height: 280,
                objectFit: "cover",
              }}
            />
          ) : (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: "100%",
                height: "100%",
                fontSize: 96,
                fontWeight: 800,
                color: brand.colors.green,
              }}
            >
              {initials}
            </div>
          )}
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            marginTop: 36,
            paddingLeft: 64,
            paddingRight: 64,
          }}
        >
          <div
            style={{
              display: "flex",
              fontSize: 56,
              fontWeight: 800,
              letterSpacing: -1,
              textAlign: "center",
              maxWidth: 1000,
            }}
          >
            {name.slice(0, 48)}
          </div>
          {subtitle ? (
            <div
              style={{
                display: "flex",
                marginTop: 12,
                fontSize: 28,
                fontWeight: 600,
                color: brand.colors.softGray,
                textAlign: "center",
              }}
            >
              {subtitle}
            </div>
          ) : null}
          <div
            style={{
              display: "flex",
              marginTop: 28,
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: 4,
              textTransform: "uppercase",
              color: brand.colors.green,
            }}
          >
            {brand.name}
          </div>
        </div>
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
