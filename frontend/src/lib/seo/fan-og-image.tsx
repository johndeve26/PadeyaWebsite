/**
 * Premium Fan Passport share card (1200×630).
 * Identity / stamps / scenes — no cover banner (distinct from Host Legacy OG).
 */

import { ImageResponse } from "next/og";

import { brand } from "@/lib/brand";
import {
  FAN_OG_DIM,
  FAN_OG_GOLD,
  FAN_OG_MUTED,
  fanOgBio,
  fanOgDisplayName,
  fanOgLocation,
  fanOgScenes,
  fanOgShareHandle,
  fanOgShowVerified,
  fanOgStampChips,
  fanOgStats,
  fanOgUsername,
  pickFanAvatarUrl,
  type FanOgStampChip,
  type FanOgStat,
} from "@/lib/seo/fan-og-presentation";
import {
  fetchRasterAsDataUrl,
  initialsFromName,
  loadBrandLogoDataUrl,
} from "@/lib/seo/og-raster";
import {
  PROFILE_OG_CONTENT_TYPE,
  PROFILE_OG_SIZE,
} from "@/lib/seo/profile-og-size";
import type { FanPassportPublicPage } from "@/lib/types/passport";

export { PROFILE_OG_CONTENT_TYPE, PROFILE_OG_SIZE };

const AVATAR = 230;
const PAD_X = 56;
const PAD_Y = 42;

function StatRow({ stat }: { stat: FanOgStat }) {
  const accent = stat.emphasize ? FAN_OG_GOLD : brand.colors.green;
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        marginBottom: 18,
      }}
    >
      <div
        style={{
          display: "flex",
          width: 14,
          height: 14,
          borderRadius: stat.key === "stamps" ? 3 : 7,
          backgroundColor: accent,
          marginRight: 14,
        }}
      />
      <div style={{ display: "flex", flexDirection: "column" }}>
        <div
          style={{
            display: "flex",
            fontSize: stat.emphasize ? 42 : 36,
            fontWeight: 800,
            color: accent,
            lineHeight: 1,
            letterSpacing: -0.8,
          }}
        >
          {stat.value}
        </div>
        <div
          style={{
            display: "flex",
            fontSize: 14,
            fontWeight: 700,
            letterSpacing: 1.2,
            color: FAN_OG_MUTED,
            marginTop: 4,
          }}
        >
          {stat.label}
        </div>
      </div>
    </div>
  );
}

function StampChip({ chip }: { chip: FanOgStampChip }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: 72,
        height: 72,
        borderRadius: 36,
        border: `2px solid ${chip.color}`,
        backgroundColor: "rgba(0,0,0,0.45)",
        marginRight: 10,
        opacity: 0.92,
      }}
    >
      <div
        style={{
          display: "flex",
          fontSize: 16,
          fontWeight: 800,
          color: chip.color,
        }}
      >
        {chip.initials}
      </div>
      <div
        style={{
          display: "flex",
          fontSize: 8,
          fontWeight: 700,
          color: FAN_OG_MUTED,
          marginTop: 2,
          maxWidth: 60,
          textAlign: "center",
          justifyContent: "center",
        }}
      >
        {chip.label}
      </div>
    </div>
  );
}

export async function buildFanPassportOgImage(
  page: FanPassportPublicPage | null,
): Promise<Response> {
  const displayName = page ? fanOgDisplayName(page) : "Fan Passport";
  const username = page ? fanOgUsername(page) : "";
  const location = page ? fanOgLocation(page) : null;
  const bio = page ? fanOgBio(page) : "Verified nights, stamps and scenes on Pàdéyá";
  const scenes = page ? fanOgScenes(page) : null;
  const verified = page ? fanOgShowVerified(page) : false;
  const stats = page ? fanOgStats(page) : [];
  const stamps = page ? fanOgStampChips(page) : [];
  const shareHandle = page ? fanOgShareHandle(page) : "padeya.com";
  const handleLine = [username, location].filter(Boolean).join(" · ");
  const avatarUrl = page ? pickFanAvatarUrl(page) : null;
  const initials = initialsFromName(displayName);

  const [avatar, logo] = await Promise.all([
    fetchRasterAsDataUrl(avatarUrl),
    loadBrandLogoDataUrl(),
  ]);

  const response = new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          position: "relative",
          backgroundColor: "#0A0A0A",
          color: brand.colors.paper,
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
          overflow: "hidden",
        }}
      >
        {/* Atmosphere */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            backgroundImage:
              "radial-gradient(circle at 12% 18%, rgba(142,240,18,0.16) 0%, transparent 42%), radial-gradient(circle at 88% 78%, rgba(212,175,55,0.12) 0%, transparent 40%), linear-gradient(135deg, #111111 0%, #050505 55%, #0b1208 100%)",
          }}
        />

        {/* Soft passport ring behind avatar */}
        <div
          style={{
            position: "absolute",
            left: PAD_X - 18,
            top: 150,
            width: AVATAR + 56,
            height: AVATAR + 56,
            borderRadius: (AVATAR + 56) / 2,
            display: "flex",
            border: "2px solid rgba(142,240,18,0.18)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: PAD_X - 4,
            top: 164,
            width: AVATAR + 28,
            height: AVATAR + 28,
            borderRadius: (AVATAR + 28) / 2,
            display: "flex",
            border: "1px solid rgba(212,175,55,0.28)",
          }}
        />

        {/* Brand logo */}
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
              height={40}
              width={122}
              alt=""
              style={{ height: 40, width: 122, objectFit: "contain" }}
            />
          ) : (
            <div
              style={{
                display: "flex",
                fontSize: 24,
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
            left: PAD_X + 10,
            top: 178,
            width: AVATAR,
            height: AVATAR,
            display: "flex",
            borderRadius: AVATAR / 2,
            border: `6px solid ${FAN_OG_GOLD}`,
            boxShadow: "0 0 0 3px rgba(142,240,18,0.55), 0 18px 40px rgba(0,0,0,0.55)",
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
                fontSize: 72,
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

        {verified ? (
          <div
            style={{
              position: "absolute",
              left: PAD_X + 10 + AVATAR - 48,
              top: 178 + AVATAR - 44,
              width: 44,
              height: 44,
              borderRadius: 22,
              backgroundColor: brand.colors.green,
              border: "3px solid #000",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                display: "flex",
                width: 14,
                height: 14,
                borderRadius: 7,
                backgroundColor: "#000",
              }}
            />
          </div>
        ) : null}

        {/* Centre identity */}
        <div
          style={{
            position: "absolute",
            left: PAD_X + AVATAR + 56,
            top: 118,
            width: 430,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              marginBottom: 12,
            }}
          >
            <div
              style={{
                display: "flex",
                fontSize: 16,
                fontWeight: 800,
                letterSpacing: 3,
                color: brand.colors.green,
              }}
            >
              FAN PASSPORT
            </div>
            <div
              style={{
                display: "flex",
                flex: 1,
                height: 2,
                backgroundColor: "rgba(142,240,18,0.35)",
                marginLeft: 12,
              }}
            />
          </div>

          <div
            style={{
              display: "flex",
              fontSize: 40,
              fontWeight: 800,
              letterSpacing: -1,
              lineHeight: 1.08,
              color: brand.colors.paper,
              marginBottom: 8,
              maxWidth: 420,
            }}
          >
            {displayName}
          </div>

          {handleLine ? (
            <div
              style={{
                display: "flex",
                fontSize: 22,
                color: FAN_OG_MUTED,
                marginBottom: 10,
              }}
            >
              {handleLine}
            </div>
          ) : null}

          <div
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              marginBottom: 12,
            }}
          >
            {verified ? (
              <>
                <div
                  style={{
                    display: "flex",
                    width: 16,
                    height: 16,
                    borderRadius: 8,
                    backgroundColor: brand.colors.green,
                    marginRight: 8,
                  }}
                />
                <div
                  style={{
                    display: "flex",
                    fontSize: 18,
                    fontWeight: 700,
                    color: brand.colors.green,
                  }}
                >
                  Verified on {brand.name}
                </div>
              </>
            ) : (
              <div
                style={{
                  display: "flex",
                  fontSize: 18,
                  fontWeight: 700,
                  color: FAN_OG_MUTED,
                }}
              >
                Fan Passport
              </div>
            )}
          </div>

          <div
            style={{
              display: "flex",
              fontSize: 20,
              color: FAN_OG_MUTED,
              lineHeight: 1.35,
              marginBottom: scenes ? 14 : 0,
              maxWidth: 420,
            }}
          >
            {bio}
          </div>

          {scenes ? (
            <div style={{ display: "flex", flexDirection: "column" }}>
              <div
                style={{
                  display: "flex",
                  flexDirection: "row",
                  alignItems: "center",
                  marginBottom: 4,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    width: 10,
                    height: 10,
                    borderRadius: 5,
                    backgroundColor: brand.colors.green,
                    marginRight: 8,
                  }}
                />
                <div
                  style={{
                    display: "flex",
                    fontSize: 12,
                    fontWeight: 800,
                    letterSpacing: 1.4,
                    color: brand.colors.green,
                  }}
                >
                  FAVORITE SCENE
                </div>
              </div>
              <div
                style={{
                  display: "flex",
                  fontSize: 20,
                  fontWeight: 600,
                  color: brand.colors.paper,
                }}
              >
                {scenes}
              </div>
            </div>
          ) : null}
        </div>

        {/* Right seal + stats */}
        <div
          style={{
            position: "absolute",
            right: PAD_X,
            top: 96,
            width: 250,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              width: 132,
              height: 132,
              borderRadius: 66,
              border: `3px solid ${verified ? FAN_OG_GOLD : "rgba(255,255,255,0.25)"}`,
              backgroundColor: "rgba(0,0,0,0.35)",
              alignItems: "center",
              justifyContent: "center",
              flexDirection: "column",
              marginBottom: 22,
            }}
          >
            <div
              style={{
                display: "flex",
                width: 28,
                height: 28,
                borderRadius: 6,
                backgroundColor: verified ? FAN_OG_GOLD : brand.colors.green,
                marginBottom: 8,
              }}
            />
            <div
              style={{
                display: "flex",
                fontSize: 11,
                fontWeight: 800,
                letterSpacing: 1,
                color: verified ? FAN_OG_GOLD : FAN_OG_MUTED,
                textAlign: "center",
                maxWidth: 100,
                justifyContent: "center",
              }}
            >
              {verified ? "VERIFIED PASSPORT" : "FAN PASSPORT"}
            </div>
            <div
              style={{
                display: "flex",
                fontSize: 10,
                fontWeight: 700,
                color: FAN_OG_DIM,
                marginTop: 2,
              }}
            >
              ON PÀDÉYÁ
            </div>
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              width: "100%",
              paddingLeft: 12,
            }}
          >
            {stats.map((stat) => (
              <StatRow key={stat.key} stat={stat} />
            ))}
          </div>
        </div>

        {/* Bottom stamp row */}
        {stamps.length > 0 ? (
          <div
            style={{
              position: "absolute",
              left: PAD_X,
              bottom: 92,
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
            }}
          >
            {stamps.map((chip) => (
              <StampChip key={chip.key} chip={chip} />
            ))}
          </div>
        ) : page ? (
          <div
            style={{
              position: "absolute",
              left: PAD_X,
              bottom: 110,
              display: "flex",
              fontSize: 18,
              color: FAN_OG_DIM,
            }}
          >
            No stamps yet
          </div>
        ) : null}

        {/* Footer CTA */}
        <div
          style={{
            position: "absolute",
            left: PAD_X,
            right: PAD_X,
            bottom: PAD_Y - 4,
            display: "flex",
            flexDirection: "row",
            alignItems: "flex-end",
            justifyContent: "space-between",
          }}
        >
          <div
            style={{
              display: "flex",
              fontSize: 16,
              color: FAN_OG_DIM,
              maxWidth: 520,
            }}
          >
            Verified nights, stamps and scenes on {brand.name}
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-end",
            }}
          >
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                marginBottom: 4,
              }}
            >
              <div
                style={{
                  display: "flex",
                  width: 14,
                  height: 14,
                  borderRadius: 7,
                  backgroundColor: brand.colors.green,
                  marginRight: 8,
                }}
              />
              <div
                style={{
                  display: "flex",
                  fontSize: 18,
                  fontWeight: 800,
                  letterSpacing: 0.6,
                  color: brand.colors.green,
                }}
              >
                VIEW FAN PASSPORT
              </div>
            </div>
            <div
              style={{
                display: "flex",
                fontSize: 18,
                color: brand.colors.paper,
              }}
            >
              {shareHandle}
            </div>
          </div>
        </div>

        {/* Subtle outer frame */}
        <div
          style={{
            position: "absolute",
            left: 18,
            top: 18,
            right: 18,
            bottom: 18,
            display: "flex",
            borderRadius: 22,
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        />
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
      subtitle: "Fan Passport",
      avatarUrl,
    });
  }
}
