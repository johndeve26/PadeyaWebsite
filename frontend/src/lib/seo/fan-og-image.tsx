/**
 * Premium Fan Passport share card (1200×630).
 * Identity-first passport card — no cover banner; horizontal stats; progress empty state.
 */

import { ImageResponse } from "next/og";

import { brand } from "@/lib/brand";
import {
  FAN_OG_DIM,
  FAN_OG_GOLD,
  FAN_OG_MUTED,
  fanOgBio,
  fanOgDisplayName,
  fanOgDisplayNameFontSize,
  fanOgEmptyStampCopy,
  fanOgLocation,
  fanOgScenes,
  fanOgShareHandle,
  fanOgShowVerified,
  fanOgStampChips,
  fanOgStats,
  fanOgStatusLine,
  fanOgSupportCopy,
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

const AVATAR = 236;
const PAD_X = 52;
const PAD_Y = 38;

function Seal({ verified }: { verified: boolean }) {
  const accent = verified ? FAN_OG_GOLD : brand.colors.green;
  return (
    <div
      style={{
        display: "flex",
        width: 148,
        height: 148,
        borderRadius: 74,
        border: `3px solid ${accent}`,
        backgroundColor: "rgba(0,0,0,0.45)",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        boxShadow: `0 0 24px ${verified ? "rgba(212,175,55,0.25)" : "rgba(142,240,18,0.22)"}`,
      }}
    >
      <div
        style={{
          display: "flex",
          width: 26,
          height: 26,
          borderRadius: 6,
          backgroundColor: accent,
          marginBottom: 8,
        }}
      />
      <div
        style={{
          display: "flex",
          fontSize: 12,
          fontWeight: 800,
          letterSpacing: 1.2,
          color: accent,
        }}
      >
        {verified ? "VERIFIED" : "PUBLIC"}
      </div>
      <div
        style={{
          display: "flex",
          fontSize: 11,
          fontWeight: 800,
          letterSpacing: 1,
          color: brand.colors.paper,
          marginTop: 2,
        }}
      >
        FAN PASSPORT
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
  );
}

function StatColumn({ stat }: { stat: FanOgStat }) {
  const color = stat.active ? brand.colors.green : FAN_OG_MUTED;
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        flex: 1,
      }}
    >
      <div
        style={{
          display: "flex",
          fontSize: 48,
          fontWeight: 800,
          color,
          lineHeight: 1,
          letterSpacing: -1,
        }}
      >
        {stat.value}
      </div>
      <div
        style={{
          display: "flex",
          fontSize: 15,
          fontWeight: 700,
          letterSpacing: 1.1,
          color: FAN_OG_DIM,
          marginTop: 8,
        }}
      >
        {stat.label}
      </div>
    </div>
  );
}

function StampChip({ chip }: { chip: FanOgStampChip }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        border: `2px solid ${chip.color}`,
        borderRadius: 999,
        padding: "6px 12px",
        marginRight: 8,
        backgroundColor: "rgba(0,0,0,0.4)",
      }}
    >
      <div
        style={{
          display: "flex",
          fontSize: 14,
          fontWeight: 800,
          color: chip.color,
          marginRight: 6,
        }}
      >
        {chip.initials}
      </div>
      <div
        style={{
          display: "flex",
          fontSize: 12,
          fontWeight: 600,
          color: FAN_OG_MUTED,
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
  if (!page) {
    const { buildProfileOgImage } = await import("@/lib/seo/profile-og-image");
    return buildProfileOgImage({
      displayName: "Fan Passport",
      subtitle: "Pàdéyá",
      avatarUrl: null,
    });
  }

  const displayName = fanOgDisplayName(page);
  const nameSize = fanOgDisplayNameFontSize(displayName);
  const username = fanOgUsername(page);
  const location = fanOgLocation(page);
  const bio = fanOgBio(page);
  const scenes = fanOgScenes(page);
  const verified = fanOgShowVerified(page);
  const statusLine = fanOgStatusLine(page);
  const stats = fanOgStats(page);
  const stampPack = fanOgStampChips(page);
  const emptyStamp = fanOgEmptyStampCopy(page);
  const support = fanOgSupportCopy(page);
  const shareHandle = fanOgShareHandle(page);
  const handleLine = [username, location].filter(Boolean).join(" · ");
  const avatarUrl = pickFanAvatarUrl(page);
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
          backgroundColor: "#080808",
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
              "radial-gradient(circle at 14% 22%, rgba(142,240,18,0.14) 0%, transparent 40%), radial-gradient(circle at 90% 12%, rgba(212,175,55,0.10) 0%, transparent 36%), linear-gradient(160deg, #101010 0%, #070707 55%, #0a1208 100%)",
          }}
        />

        {/* Contour rings behind avatar */}
        <div
          style={{
            position: "absolute",
            left: PAD_X - 10,
            top: 118,
            width: AVATAR + 48,
            height: AVATAR + 48,
            borderRadius: (AVATAR + 48) / 2,
            display: "flex",
            border: "2px solid rgba(142,240,18,0.16)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: PAD_X + 4,
            top: 132,
            width: AVATAR + 20,
            height: AVATAR + 20,
            borderRadius: (AVATAR + 20) / 2,
            display: "flex",
            border: "1px solid rgba(212,175,55,0.28)",
          }}
        />

        {/* Top: logo + seal */}
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
              height={36}
              width={110}
              alt=""
              style={{ height: 36, width: 110, objectFit: "contain" }}
            />
          ) : (
            <div
              style={{
                display: "flex",
                fontSize: 22,
                fontWeight: 800,
                letterSpacing: 3,
                color: brand.colors.green,
              }}
            >
              {brand.name.toUpperCase()}
            </div>
          )}
        </div>
        <div
          style={{
            position: "absolute",
            top: 28,
            right: PAD_X,
            display: "flex",
          }}
        >
          <Seal verified={verified} />
        </div>

        {/* Avatar */}
        <div
          style={{
            position: "absolute",
            left: PAD_X + 14,
            top: 142,
            width: AVATAR,
            height: AVATAR,
            display: "flex",
            borderRadius: AVATAR / 2,
            border: `6px solid ${FAN_OG_GOLD}`,
            boxShadow:
              "0 0 0 3px rgba(142,240,18,0.45), 0 16px 36px rgba(0,0,0,0.55)",
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
              left: PAD_X + 14 + AVATAR - 46,
              top: 142 + AVATAR - 42,
              width: 42,
              height: 42,
              borderRadius: 21,
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

        {/* Identity column */}
        <div
          style={{
            position: "absolute",
            left: PAD_X + AVATAR + 48,
            top: 118,
            width: 520,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              marginBottom: 10,
            }}
          >
            <div
              style={{
                display: "flex",
                fontSize: 18,
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
                maxWidth: 180,
              }}
            />
          </div>

          <div
            style={{
              display: "flex",
              fontSize: nameSize,
              fontWeight: 800,
              letterSpacing: -1,
              lineHeight: 1.05,
              color: brand.colors.paper,
              marginBottom: 8,
              maxWidth: 500,
            }}
          >
            {displayName}
          </div>

          {handleLine ? (
            <div
              style={{
                display: "flex",
                fontSize: 24,
                color: FAN_OG_MUTED,
                marginBottom: 8,
              }}
            >
              {handleLine}
            </div>
          ) : null}

          <div
            style={{
              display: "flex",
              fontSize: 18,
              fontWeight: 700,
              color: verified ? brand.colors.green : FAN_OG_MUTED,
              marginBottom: 10,
            }}
          >
            {statusLine}
          </div>

          <div
            style={{
              display: "flex",
              fontSize: 24,
              color: FAN_OG_MUTED,
              lineHeight: 1.3,
              maxWidth: 500,
              marginBottom: scenes ? 10 : 0,
            }}
          >
            {bio}
          </div>

          {scenes ? (
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
                  fontSize: 18,
                  fontWeight: 600,
                  color: brand.colors.paper,
                }}
              >
                {scenes}
              </div>
            </div>
          ) : null}
        </div>

        {/* Horizontal stats bar */}
        <div
          style={{
            position: "absolute",
            left: PAD_X,
            right: PAD_X,
            top: 400,
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "18px 28px",
            borderRadius: 18,
            border: "1px solid rgba(255,255,255,0.10)",
            backgroundColor: "rgba(0,0,0,0.42)",
          }}
        >
          {stats.map((stat, i) => (
            <div
              key={stat.key}
              style={{
                display: "flex",
                flex: 1,
                flexDirection: "row",
                alignItems: "center",
              }}
            >
              {i > 0 ? (
                <div
                  style={{
                    display: "flex",
                    width: 1,
                    height: 56,
                    backgroundColor: "rgba(142,240,18,0.25)",
                    marginRight: 8,
                  }}
                />
              ) : null}
              <StatColumn stat={stat} />
            </div>
          ))}
        </div>

        {/* Stamp progress / chips */}
        <div
          style={{
            position: "absolute",
            left: PAD_X,
            right: 420,
            top: 508,
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
          }}
        >
          {emptyStamp ? (
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                border: `1px solid rgba(212,175,55,0.45)`,
                borderRadius: 14,
                padding: "12px 16px",
                backgroundColor: "rgba(0,0,0,0.4)",
                maxWidth: 520,
              }}
            >
              <div
                style={{
                  display: "flex",
                  width: 18,
                  height: 18,
                  borderRadius: 4,
                  backgroundColor: FAN_OG_GOLD,
                  marginRight: 12,
                }}
              />
              <div
                style={{
                  display: "flex",
                  fontSize: 18,
                  color: FAN_OG_MUTED,
                  lineHeight: 1.25,
                }}
              >
                {emptyStamp}
              </div>
            </div>
          ) : (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "row",
                  alignItems: "center",
                  marginBottom: 6,
                }}
              >
                {stampPack.chips.map((chip) => (
                  <StampChip key={chip.key} chip={chip} />
                ))}
                {stampPack.extra > 0 ? (
                  <div
                    style={{
                      display: "flex",
                      fontSize: 16,
                      fontWeight: 800,
                      color: brand.colors.green,
                    }}
                  >
                    +{stampPack.extra}
                  </div>
                ) : null}
              </div>
              {stampPack.summary ? (
                <div
                  style={{
                    display: "flex",
                    fontSize: 15,
                    color: FAN_OG_DIM,
                  }}
                >
                  {stampPack.summary}
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Bottom support + CTA */}
        <div
          style={{
            position: "absolute",
            left: PAD_X,
            bottom: PAD_Y - 2,
            display: "flex",
            fontSize: 16,
            color: FAN_OG_DIM,
            maxWidth: 380,
          }}
        >
          {support}
        </div>

        <div
          style={{
            position: "absolute",
            right: PAD_X,
            bottom: PAD_Y - 6,
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-end",
            border: `2px solid rgba(142,240,18,0.55)`,
            borderRadius: 16,
            padding: "12px 18px",
            backgroundColor: "rgba(0,0,0,0.5)",
          }}
        >
          <div
            style={{
              display: "flex",
              fontSize: 18,
              fontWeight: 800,
              letterSpacing: 0.8,
              color: brand.colors.green,
              marginBottom: 4,
            }}
          >
            VIEW FAN PASSPORT →
          </div>
          <div
            style={{
              display: "flex",
              fontSize: 17,
              color: brand.colors.paper,
            }}
          >
            {shareHandle}
          </div>
        </div>

        {/* Outer frame */}
        <div
          style={{
            position: "absolute",
            left: 16,
            top: 16,
            right: 16,
            bottom: 16,
            display: "flex",
            borderRadius: 20,
            border: "1px solid rgba(255,255,255,0.07)",
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
