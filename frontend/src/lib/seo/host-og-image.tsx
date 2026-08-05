/**
 * Premium Host Legacy share card (1200×630) for WhatsApp / X / Facebook / etc.
 *
 * Cover + avatar + trust stats — live data from the public Legacy payload.
 * Fan Passport continues to use the simpler profile-og-image DP card.
 */

import { ImageResponse } from "next/og";

import { brand } from "@/lib/brand";
import {
  HOST_OG_GOLD,
  HOST_OG_MUTED,
  HOST_OG_PANEL,
  hostOgBio,
  hostOgDisplayName,
  hostOgLegacyScore,
  hostOgLocation,
  hostOgShareHandle,
  hostOgStats,
  hostOgUsername,
  pickHostMediaUrl,
  splitDisplayNameTone,
  type HostOgStat,
} from "@/lib/seo/host-og-presentation";
import {
  fetchRasterAsDataUrl,
  initialsFromName,
  loadBrandLogoDataUrl,
} from "@/lib/seo/og-raster";
import {
  PROFILE_OG_CONTENT_TYPE,
  PROFILE_OG_SIZE,
} from "@/lib/seo/profile-og-size";
import type { LegacyPage } from "@/lib/types/legacy";

export { PROFILE_OG_CONTENT_TYPE, PROFILE_OG_SIZE };

const W = PROFILE_OG_SIZE.width;
const H = PROFILE_OG_SIZE.height;
const AVATAR = 162;
const PAD_X = 56;
const PAD_Y = 40;

function StatGlyph({
  icon,
  color,
}: {
  icon: HostOgStat["icon"];
  color: string;
}) {
  if (icon === "star") {
    return (
      <div
        style={{
          display: "flex",
          width: 14,
          height: 14,
          borderRadius: 7,
          backgroundColor: color,
          marginRight: 10,
        }}
      />
    );
  }
  if (icon === "ticket") {
    return (
      <div
        style={{
          display: "flex",
          width: 22,
          height: 14,
          borderRadius: 4,
          border: `2px solid ${color}`,
          marginRight: 10,
        }}
      />
    );
  }
  // calendar
  return (
    <div
      style={{
        display: "flex",
        width: 18,
        height: 18,
        borderRadius: 3,
        border: `2px solid ${color}`,
        marginRight: 10,
      }}
    />
  );
}

function BadgePill({
  label,
  color,
  kind,
}: {
  label: string;
  color: string;
  kind: "verified" | "legacy";
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        border: `2px solid ${color}`,
        borderRadius: 999,
        padding: "6px 14px",
        marginRight: 10,
        color,
        fontSize: 18,
        fontWeight: 700,
        letterSpacing: 0.2,
      }}
    >
      {kind === "verified" ? (
        <div
          style={{
            display: "flex",
            width: 16,
            height: 16,
            borderRadius: 8,
            backgroundColor: color,
            marginRight: 8,
          }}
        />
      ) : (
        <div
          style={{
            display: "flex",
            width: 12,
            height: 12,
            borderRadius: 2,
            backgroundColor: color,
            marginRight: 10,
          }}
        />
      )}
      <div style={{ display: "flex" }}>{label}</div>
    </div>
  );
}

export async function buildHostLegacyOgImage(
  page: LegacyPage | null,
): Promise<Response> {
  const displayName = page ? hostOgDisplayName(page) : "Host";
  const { lead, accent } = splitDisplayNameTone(displayName);
  const username = page ? hostOgUsername(page) : "";
  const location = page ? hostOgLocation(page) : null;
  const bio = page ? hostOgBio(page) : null;
  const verified = Boolean(page?.verified);
  const legacyScore = page ? hostOgLegacyScore(page) : null;
  const stats = page ? hostOgStats(page) : [];
  const shareHandle = page ? hostOgShareHandle(page) : "padeya.com";
  const handleLine = [username, location].filter(Boolean).join(" · ");

  const coverUrl = page
    ? pickHostMediaUrl(page.profile?.cover_media, page.profile?.cover_url)
    : null;
  const avatarUrl = page
    ? pickHostMediaUrl(page.profile?.avatar_media, page.profile?.avatar_url)
    : null;

  const [cover, avatar, logo] = await Promise.all([
    fetchRasterAsDataUrl(coverUrl),
    fetchRasterAsDataUrl(avatarUrl),
    loadBrandLogoDataUrl(),
  ]);

  const initials = initialsFromName(displayName);

  const response = new ImageResponse(
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
        {/* Cover or branded fallback */}
        {cover ? (
          // eslint-disable-next-line @next/next/no-img-element -- ImageResponse
          <img
            src={cover}
            width={W}
            height={H}
            alt=""
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: W,
              height: H,
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
              backgroundImage:
                "radial-gradient(circle at 22% 18%, #1a2e14 0%, #0a0a0a 42%, #000000 78%), linear-gradient(135deg, rgba(142,240,18,0.12) 0%, transparent 45%)",
            }}
          />
        )}

        {/* Left scrim */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            backgroundImage:
              "linear-gradient(to right, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.45) 42%, rgba(0,0,0,0.18) 70%, rgba(0,0,0,0.35) 100%)",
          }}
        />

        {/* Soft green ambient */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            backgroundImage:
              "radial-gradient(circle at 70% 30%, rgba(142,240,18,0.14) 0%, transparent 42%)",
          }}
        />

        {/* Bottom grade */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            height: 360,
            display: "flex",
            backgroundImage:
              "linear-gradient(to top, rgba(0,0,0,0.94) 0%, rgba(0,0,0,0.72) 38%, rgba(0,0,0,0.2) 78%, rgba(0,0,0,0) 100%)",
          }}
        />

        {/* Subtle geometric lines when no cover */}
        {!cover ? (
          <div
            style={{
              position: "absolute",
              right: 80,
              top: 90,
              width: 280,
              height: 280,
              display: "flex",
              border: "1px solid rgba(142,240,18,0.18)",
              borderRadius: 24,
              opacity: 0.7,
            }}
          />
        ) : null}

        {/* Brand mark */}
        <div
          style={{
            position: "absolute",
            top: PAD_Y,
            left: PAD_X,
            display: "flex",
            alignItems: "center",
          }}
        >
          {logo ? (
            // eslint-disable-next-line @next/next/no-img-element -- ImageResponse
            <img
              src={logo}
              height={42}
              width={128}
              alt=""
              style={{ height: 42, width: 128, objectFit: "contain" }}
            />
          ) : (
            <div
              style={{
                display: "flex",
                fontSize: 26,
                fontWeight: 800,
                letterSpacing: 3,
                color: brand.colors.green,
                textTransform: "uppercase",
              }}
            >
              {brand.name}
            </div>
          )}
        </div>

        {/* Avatar */}
        <div
          style={{
            position: "absolute",
            left: PAD_X,
            bottom: 168,
            width: AVATAR,
            height: AVATAR,
            display: "flex",
            borderRadius: AVATAR / 2,
            border: `5px solid ${HOST_OG_GOLD}`,
            boxShadow: "0 12px 40px rgba(0,0,0,0.55)",
            overflow: "hidden",
            backgroundColor: "#111",
          }}
        >
          {avatar ? (
            // eslint-disable-next-line @next/next/no-img-element -- ImageResponse
            <img
              src={avatar}
              width={AVATAR}
              height={AVATAR}
              alt=""
              style={{
                width: AVATAR,
                height: AVATAR,
                objectFit: "cover",
                objectPosition: "center",
              }}
            />
          ) : (
            <div
              style={{
                width: "100%",
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 56,
                fontWeight: 800,
                color: brand.colors.green,
                backgroundImage:
                  "radial-gradient(circle at 30% 20%, #222 0%, #000 75%)",
              }}
            >
              {initials}
            </div>
          )}
        </div>

        {/* Verified badge on avatar */}
        {verified ? (
          <div
            style={{
              position: "absolute",
              left: PAD_X + AVATAR - 42,
              bottom: 168 - 6,
              width: 44,
              height: 44,
              borderRadius: 22,
              backgroundColor: brand.colors.green,
              border: "3px solid #000",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#000",
              fontSize: 18,
              fontWeight: 900,
            }}
          >
            <div
              style={{
                display: "flex",
                width: 12,
                height: 12,
                borderRadius: 6,
                backgroundColor: "#000",
              }}
            />
          </div>
        ) : null}

        {/* Info panel */}
        <div
          style={{
            position: "absolute",
            left: PAD_X + AVATAR + 28,
            right: PAD_X,
            bottom: 118,
            display: "flex",
            flexDirection: "column",
            backgroundColor: HOST_OG_PANEL,
            borderRadius: 18,
            padding: "22px 26px 20px",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          {/* Name */}
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              flexWrap: "nowrap",
              fontSize: 52,
              fontWeight: 800,
              letterSpacing: -1.2,
              lineHeight: 1.05,
              marginBottom: 6,
            }}
          >
            <div style={{ display: "flex", color: brand.colors.paper }}>
              {lead}
            </div>
            {accent ? (
              <div
                style={{
                  display: "flex",
                  color: brand.colors.green,
                  marginLeft: 12,
                }}
              >
                {accent}
              </div>
            ) : null}
          </div>

          {handleLine ? (
            <div
              style={{
                display: "flex",
                fontSize: 22,
                color: HOST_OG_MUTED,
                marginBottom: 12,
              }}
            >
              {handleLine}
            </div>
          ) : null}

          {/* Badges */}
          {(verified || legacyScore != null) && (
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                marginBottom: 14,
              }}
            >
              {verified ? (
                <BadgePill
                  label="Verified Host"
                  color={brand.colors.green}
                  kind="verified"
                />
              ) : null}
              {legacyScore != null ? (
                <BadgePill
                  label={`Legacy ${legacyScore}`}
                  color={HOST_OG_GOLD}
                  kind="legacy"
                />
              ) : null}
            </div>
          )}

          {/* Stats */}
          {stats.length > 0 ? (
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                flexWrap: "wrap",
                marginBottom: bio ? 12 : 0,
              }}
            >
              {stats.map((stat, i) => (
                <div
                  key={stat.key}
                  style={{
                    display: "flex",
                    flexDirection: "row",
                    alignItems: "center",
                    marginRight: 18,
                  }}
                >
                  {i > 0 ? (
                    <div
                      style={{
                        display: "flex",
                        width: 5,
                        height: 5,
                        borderRadius: 3,
                        backgroundColor: "rgba(255,255,255,0.35)",
                        marginRight: 18,
                      }}
                    />
                  ) : null}
                  <StatGlyph
                    icon={stat.icon}
                    color={
                      stat.icon === "star" ? HOST_OG_GOLD : brand.colors.green
                    }
                  />
                  <div
                    style={{
                      display: "flex",
                      fontSize: 20,
                      fontWeight: 600,
                      color: brand.colors.paper,
                    }}
                  >
                    {stat.label}
                  </div>
                </div>
              ))}
            </div>
          ) : null}

          {bio ? (
            <div
              style={{
                display: "flex",
                fontSize: 20,
                color: HOST_OG_MUTED,
                lineHeight: 1.35,
                maxWidth: 820,
              }}
            >
              {bio}
            </div>
          ) : null}
        </div>

        {/* CTA + URL */}
        <div
          style={{
            position: "absolute",
            left: PAD_X,
            right: PAD_X,
            bottom: PAD_Y,
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
            }}
          >
            <div
              style={{
                display: "flex",
                width: 34,
                height: 34,
                borderRadius: 17,
                backgroundColor: brand.colors.green,
                alignItems: "center",
                justifyContent: "center",
                color: "#000",
                fontSize: 18,
                fontWeight: 900,
                marginRight: 12,
              }}
            >
              <div
                style={{
                  display: "flex",
                  width: 12,
                  height: 12,
                  borderRadius: 2,
                  backgroundColor: "#000",
                }}
              />
            </div>
            <div style={{ display: "flex", fontSize: 22, fontWeight: 700 }}>
              <div style={{ display: "flex", color: brand.colors.green }}>
                View Legacy
              </div>
              <div
                style={{
                  display: "flex",
                  color: brand.colors.paper,
                  marginLeft: 8,
                }}
              >
                on {brand.name}
              </div>
            </div>
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              fontSize: 20,
              color: HOST_OG_MUTED,
            }}
          >
            {shareHandle}
          </div>
        </div>
      </div>
    ),
    {
      ...PROFILE_OG_SIZE,
      headers: {
        "Cache-Control":
          "public, max-age=120, s-maxage=120, stale-while-revalidate=3600",
      },
    },
  );

  // Render eagerly so WebP/Satori failures can fall back (lazy body read would 500).
  try {
    const buf = await response.arrayBuffer();
    return new Response(buf, {
      status: 200,
      headers: {
        "Content-Type": PROFILE_OG_CONTENT_TYPE,
        "Cache-Control":
          "public, max-age=120, s-maxage=120, stale-while-revalidate=3600",
      },
    });
  } catch {
    const { buildProfileOgImage } = await import("@/lib/seo/profile-og-image");
    return buildProfileOgImage({
      displayName,
      subtitle: "Host on Pàdéyá",
      avatarUrl,
    });
  }
}
