/**
 * Profile share cards — image-first DP showcase (1200×630).
 *
 * Used as a fallback when richer Host/Fan OG cards fail to render.
 * Host Legacy → `host-og-image`. Fan Passport → `fan-og-image`.
 */

import { ImageResponse } from "next/og";

import { brand } from "@/lib/brand";
import {
  fetchRasterAsDataUrl,
  initialsFromName,
} from "@/lib/seo/og-raster";
import { PROFILE_OG_SIZE } from "@/lib/seo/profile-og-size";

export { PROFILE_OG_CONTENT_TYPE, PROFILE_OG_SIZE } from "@/lib/seo/profile-og-size";

export async function buildProfileOgImage(opts: {
  displayName: string;
  subtitle: string;
  avatarUrl?: string | null;
}): Promise<ImageResponse> {
  const name = opts.displayName.trim() || brand.name;
  const subtitle = opts.subtitle.trim();
  const avatar = await fetchRasterAsDataUrl(opts.avatarUrl);
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
