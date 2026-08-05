import type { Metadata } from "next";

import {
  fanOgDescription,
  fanOgTitle,
} from "@/lib/seo/fan-og-presentation";
import { PROFILE_OG_SIZE } from "@/lib/seo/profile-og-size";
import { absoluteUrl, buildPageMetadata } from "@/lib/seo/site";
import { resolvePublicAssetUrl } from "@/lib/seo/public-asset";
import type { FanPassportPublicPage } from "@/lib/types/passport";

export function fanPassportCanonicalPath(username: string): string {
  return `/f/${encodeURIComponent(username.replace(/^@/, "").trim())}`;
}

export function fanPassportOgImagePath(username: string): string {
  return `${fanPassportCanonicalPath(username)}/opengraph-image`;
}

export function isFanPassportIndexable(
  page: Pick<FanPassportPublicPage, "visibility">,
): boolean {
  return page.visibility === "public";
}

export function buildFanMetadata(page: FanPassportPublicPage): Metadata {
  const meta = buildPageMetadata({
    title: fanOgTitle(page),
    description: fanOgDescription(page),
    path: fanPassportCanonicalPath(page.username),
    // Same-origin dynamic passport card (never raw multi‑MB avatar).
    image: fanPassportOgImagePath(page.username),
    ogImageWidth: PROFILE_OG_SIZE.width,
    ogImageHeight: PROFILE_OG_SIZE.height,
    noIndex: !isFanPassportIndexable(page),
  });

  const ogImages = meta.openGraph?.images;
  const first = Array.isArray(ogImages) ? ogImages[0] : ogImages;
  const alt = `${page.display_name.trim() || "Fan"}'s Fan Passport on Pàdéyá`;
  const withAlt =
    first && typeof first === "object"
      ? Array.isArray(ogImages)
        ? [{ ...first, alt }]
        : { ...first, alt }
      : ogImages;

  return {
    ...meta,
    openGraph: {
      ...meta.openGraph,
      type: "profile",
      images: withAlt,
    } as Metadata["openGraph"],
  };
}

/** ProfilePage → Person for genuinely public Fan Passports only. */
export function fanPassportJsonLd(
  page: FanPassportPublicPage,
): Record<string, unknown> | null {
  if (!isFanPassportIndexable(page)) return null;

  const url = absoluteUrl(fanPassportCanonicalPath(page.username));
  const description =
    page.tagline ||
    page.bio ||
    `${page.display_name}'s Fan Passport on Pàdéyá`;
  const image = resolvePublicAssetUrl(page.avatar_url) || undefined;

  const person: Record<string, unknown> = {
    "@type": "Person",
    "@id": `${url}#person`,
    name: page.display_name,
    url,
    description: String(description).slice(0, 300),
  };
  if (image) person.image = image;

  return {
    "@context": "https://schema.org",
    "@type": "ProfilePage",
    name: `${page.display_name} · Fan Passport`,
    url,
    mainEntity: person,
  };
}
