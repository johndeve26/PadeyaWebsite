/**
 * Premium public Event share card (1200×630).
 * Event-first — never host avatar / Legacy / Fan Passport styling.
 */

import { ImageResponse } from "next/og";

import { brand } from "@/lib/brand";
import { fitEventTitle } from "@/lib/seo/event-og-title";
import {
  classifyImageAspect,
  EVENT_OG_DIM,
  EVENT_OG_GOLD,
  EVENT_OG_MUTED,
  eventOgCategory,
  eventOgDateBlock,
  eventOgHostLine,
  eventOgLocation,
  eventOgPriceLabel,
  eventOgPrivacyNote,
  eventOgStatusBadge,
  eventOgTagline,
  eventOgWhenLine,
  pickEventOgMedia,
  selectEventOgLayout,
} from "@/lib/seo/event-og-presentation";
import {
  fetchRasterWithMeta,
  loadBrandLogoDataUrl,
} from "@/lib/seo/og-raster";
import {
  PROFILE_OG_CONTENT_TYPE,
  PROFILE_OG_SIZE,
} from "@/lib/seo/profile-og-size";
import { splitDisplayNameTone } from "@/lib/seo/host-og-presentation";
import type { EventItem } from "@/lib/types/events";

export { PROFILE_OG_CONTENT_TYPE, PROFILE_OG_SIZE };

const PAD_X = 56;
const PAD_Y = 42;

function TitleLines({
  lines,
  fontSize,
  letterSpacing,
  maxWidth,
}: {
  lines: string[];
  fontSize: number;
  letterSpacing: number;
  maxWidth: number;
}) {
  const full = lines.join(" ");
  const { accent } = splitDisplayNameTone(full);
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        maxWidth,
      }}
    >
      {lines.map((line, i) => {
        const isLast = i === lines.length - 1;
        if (!isLast || !accent || !line.endsWith(accent)) {
          return (
            <div
              key={`t-${i}`}
              style={{
                display: "flex",
                fontSize,
                fontWeight: 800,
                letterSpacing,
                lineHeight: 1.08,
                color: brand.colors.paper,
              }}
            >
              {line}
            </div>
          );
        }
        const prefix = line.slice(0, line.length - accent.length).trimEnd();
        return (
          <div
            key={`t-${i}`}
            style={{
              display: "flex",
              flexDirection: "row",
              flexWrap: "wrap",
              fontSize,
              fontWeight: 800,
              letterSpacing,
              lineHeight: 1.08,
            }}
          >
            {prefix ? (
              <div style={{ display: "flex", color: brand.colors.paper }}>
                {prefix}
              </div>
            ) : null}
            <div
              style={{
                display: "flex",
                color: brand.colors.green,
                marginLeft: prefix ? 14 : 0,
              }}
            >
              {accent}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function DateBlock({
  month,
  day,
  weekday,
  compact,
}: {
  month: string;
  day: string;
  weekday: string;
  compact?: boolean;
}) {
  const w = compact ? 120 : 148;
  const h = compact ? 168 : 210;
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: w,
        height: h,
        borderRadius: 22,
        border: `4px solid ${brand.colors.green}`,
        backgroundColor: "rgba(0,0,0,0.78)",
        boxShadow: `0 0 28px rgba(142,240,18,0.28)`,
      }}
    >
      <div
        style={{
          display: "flex",
          fontSize: compact ? 20 : 24,
          fontWeight: 800,
          letterSpacing: 2,
          color: brand.colors.paper,
        }}
      >
        {month}
      </div>
      <div
        style={{
          display: "flex",
          fontSize: compact ? 56 : 72,
          fontWeight: 800,
          color: brand.colors.green,
          lineHeight: 1,
          marginTop: 4,
          marginBottom: 4,
        }}
      >
        {day}
      </div>
      <div
        style={{
          display: "flex",
          fontSize: compact ? 18 : 22,
          fontWeight: 800,
          letterSpacing: 2,
          color: brand.colors.green,
        }}
      >
        {weekday}
      </div>
    </div>
  );
}

function DetailRow({
  label,
  gold,
}: {
  label: string;
  gold?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        marginBottom: 8,
      }}
    >
      <div
        style={{
          display: "flex",
          width: 10,
          height: 10,
          borderRadius: 5,
          backgroundColor: gold ? EVENT_OG_GOLD : brand.colors.green,
          marginRight: 10,
        }}
      />
      <div
        style={{
          display: "flex",
          fontSize: 20,
          color: gold ? EVENT_OG_GOLD : brand.colors.paper,
          fontWeight: gold ? 700 : 600,
        }}
      >
        {label}
      </div>
    </div>
  );
}

export async function buildEventOgImage(
  event: EventItem | null,
): Promise<Response> {
  const title = event?.title?.trim() || "Event on Pàdéyá";
  const category = event ? eventOgCategory(event) : null;
  const tagline = event ? eventOgTagline(event) : null;
  const price = event ? eventOgPriceLabel(event) : null;
  const when = event ? eventOgWhenLine(event) : "";
  const location = event ? eventOgLocation(event) : null;
  const privacy = event ? eventOgPrivacyNote(event) : null;
  const host = event ? eventOgHostLine(event) : null;
  const status = event ? eventOgStatusBadge(event) : null;
  const dateBlock = event ? eventOgDateBlock(event) : null;

  const mediaPick = event ? pickEventOgMedia(event) : null;
  const [logo, raster] = await Promise.all([
    loadBrandLogoDataUrl(),
    mediaPick ? fetchRasterWithMeta(mediaPick.url) : Promise.resolve(null),
  ]);

  const aspect = raster
    ? classifyImageAspect(raster.width, raster.height)
    : null;
  const useFlyerSide =
    Boolean(raster) &&
    (aspect === "portrait" || aspect === "square") &&
    mediaPick?.source !== "social";
  // Landscape / social / banner → full-bleed background
  const bg = !useFlyerSide && raster ? raster.dataUrl : null;
  const flyer = useFlyerSide && raster ? raster.dataUrl : null;

  const titleWidth = flyer ? 520 : dateBlock ? 640 : 980;
  const titleHeight = tagline ? 200 : 260;
  const fit = fitEventTitle(title, titleWidth, titleHeight, {
    hasTagline: Boolean(tagline),
    hasFlyerSide: Boolean(flyer),
  });
  const showTagline =
    Boolean(tagline) &&
    fit.density !== "very-long" &&
    (fit.density !== "long" || fit.lines.length < 3);
  const compactDate = fit.density === "long" || fit.density === "very-long";
  const layout = selectEventOgLayout({
    density: fit.density,
    hasFlyerSide: Boolean(flyer),
    hasBackground: Boolean(bg),
  });
  void layout;

  const response = new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          position: "relative",
          backgroundColor: "#050505",
          color: brand.colors.paper,
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
          overflow: "hidden",
        }}
      >
        {/* Background */}
        {bg ? (
          // eslint-disable-next-line @next/next/no-img-element -- ImageResponse
          <img
            src={bg}
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
              backgroundImage:
                "radial-gradient(circle at 18% 20%, rgba(142,240,18,0.18) 0%, transparent 42%), radial-gradient(circle at 85% 70%, rgba(212,175,55,0.12) 0%, transparent 40%), linear-gradient(135deg, #0c0c0c 0%, #050505 50%, #0a1408 100%)",
            }}
          />
        )}

        {/* Readability overlays — photo stays visible, copy stays dominant */}
        {bg ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              backgroundColor: "rgba(0,0,0,0.58)",
            }}
          />
        ) : null}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            backgroundImage:
              "linear-gradient(to right, rgba(0,0,0,0.94) 0%, rgba(0,0,0,0.78) 38%, rgba(0,0,0,0.45) 68%, rgba(0,0,0,0.55) 100%), linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.62) 36%, rgba(0,0,0,0.40) 62%, rgba(0,0,0,0.55) 100%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            backgroundImage:
              "radial-gradient(ellipse at 20% 55%, rgba(0,0,0,0.55) 0%, transparent 52%), radial-gradient(ellipse at 78% 42%, rgba(0,0,0,0.28) 0%, transparent 48%)",
          }}
        />

        {/* Soft brand wash (subtle, never brighter than copy) */}
        <div
          style={{
            position: "absolute",
            left: 0,
            bottom: 0,
            width: 320,
            height: 200,
            display: "flex",
            backgroundImage:
              "linear-gradient(45deg, rgba(142,240,18,0.05) 0%, transparent 65%)",
          }}
        />

        {/* Brand */}
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
              height={38}
              width={116}
              alt=""
              style={{ height: 38, width: 116, objectFit: "contain" }}
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

        {/* Category / status */}
        <div
          style={{
            position: "absolute",
            top: PAD_Y,
            right: PAD_X,
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
          }}
        >
          {status ? (
            <div
              style={{
                display: "flex",
                border: `2px solid ${status === "CANCELLED" ? "#ef4444" : EVENT_OG_GOLD}`,
                borderRadius: 999,
                padding: "8px 16px",
                marginRight: category ? 10 : 0,
                fontSize: 16,
                fontWeight: 800,
                letterSpacing: 1.2,
                color:
                  status === "CANCELLED" ? "#ef4444" : EVENT_OG_GOLD,
              }}
            >
              {status}
            </div>
          ) : null}
          {category ? (
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                border: "2px solid rgba(255,255,255,0.72)",
                borderRadius: 999,
                padding: "8px 16px",
                backgroundColor: "rgba(0,0,0,0.78)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  width: 10,
                  height: 10,
                  backgroundColor: brand.colors.green,
                  marginRight: 8,
                }}
              />
              <div
                style={{
                  display: "flex",
                  fontSize: 16,
                  fontWeight: 800,
                  letterSpacing: 1.5,
                  color: brand.colors.paper,
                  textTransform: "uppercase",
                }}
              >
                {category}
              </div>
            </div>
          ) : null}
        </div>

        {/* Portrait/square flyer frame */}
        {flyer ? (
          <div
            style={{
              position: "absolute",
              right: PAD_X,
              top: 110,
              width: 280,
              height: 400,
              display: "flex",
              borderRadius: 18,
              border: `2px solid rgba(212,175,55,0.55)`,
              overflow: "hidden",
              backgroundColor: "#111",
              boxShadow: "0 18px 40px rgba(0,0,0,0.55)",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- ImageResponse */}
            <img
              src={flyer}
              width={280}
              height={400}
              alt=""
              style={{
                width: 280,
                height: 400,
                objectFit: "contain",
                objectPosition: "center",
                backgroundColor: "#0a0a0a",
              }}
            />
          </div>
        ) : null}

        {/* Date block */}
        {dateBlock && !flyer ? (
          <div
            style={{
              position: "absolute",
              right: PAD_X,
              top: 150,
              display: "flex",
            }}
          >
            <DateBlock
              month={dateBlock.month}
              day={dateBlock.day}
              weekday={dateBlock.weekday}
              compact={compactDate}
            />
          </div>
        ) : null}

        {/* Title + copy — panel behind text when photo is full-bleed */}
        <div
          style={{
            position: "absolute",
            left: PAD_X - 18,
            top: 108,
            width: titleWidth + 36,
            display: "flex",
            flexDirection: "column",
            padding: bg && !flyer ? "18px 20px 20px" : "0",
            borderRadius: 20,
            backgroundColor:
              bg && !flyer ? "rgba(0,0,0,0.42)" : "transparent",
          }}
        >
          <TitleLines
            lines={fit.lines}
            fontSize={fit.fontSize}
            letterSpacing={fit.letterSpacing}
            maxWidth={titleWidth}
          />

          {showTagline && tagline ? (
            <div
              style={{
                display: "flex",
                fontSize: 22,
                fontWeight: 600,
                color: EVENT_OG_MUTED,
                marginTop: 14,
                maxWidth: titleWidth,
              }}
            >
              {tagline}
            </div>
          ) : null}

          {price ? (
            <div
              style={{
                display: "flex",
                fontSize: 32,
                fontWeight: 800,
                color: brand.colors.green,
                marginTop: 16,
              }}
            >
              {price}
            </div>
          ) : null}

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              marginTop: 22,
            }}
          >
            {when && when !== "—" ? <DetailRow label={when} /> : null}
            {location ? <DetailRow label={location} /> : null}
            {privacy ? <DetailRow label={privacy} gold /> : null}
          </div>
        </div>

        {/* Host pill */}
        {host ? (
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: PAD_Y,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <div
              style={{
                display: "flex",
                border: `2px solid ${EVENT_OG_GOLD}`,
                borderRadius: 999,
                padding: "8px 18px",
                backgroundColor: "rgba(0,0,0,0.82)",
                fontSize: 18,
                fontWeight: 700,
                color: brand.colors.paper,
              }}
            >
              {host}
            </div>
          </div>
        ) : (
          <div
            style={{
              position: "absolute",
              left: PAD_X,
              bottom: PAD_Y,
              display: "flex",
              fontSize: 16,
              color: EVENT_OG_DIM,
            }}
          >
            Verified tickets on {brand.name}
          </div>
        )}
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
      displayName: title.slice(0, 48),
      subtitle: "Event on Pàdéyá",
      avatarUrl: null,
    });
  }
}
