import type { Metadata } from "next";

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
  const description =
    page.tagline?.trim().slice(0, 160) ||
    page.bio?.trim().slice(0, 160) ||
    `${page.display_name}'s Fan Passport on Pàdéyá — verified nights, badges, and hosts.`;

  return buildPageMetadata({
    title: `${page.display_name} · Fan Passport`,
    description,
    path: fanPassportCanonicalPath(page.username),
    // Same-origin DP card (never raw multi‑MB avatar or brand logo).
    image: fanPassportOgImagePath(page.username),
    ogImageWidth: PROFILE_OG_SIZE.width,
    ogImageHeight: PROFILE_OG_SIZE.height,
    noIndex: !isFanPassportIndexable(page),
  });
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
