import type { Metadata } from "next";

import type { LegacyPage } from "@/lib/types/legacy";
import { PROFILE_OG_SIZE } from "@/lib/seo/profile-og-size";
import { resolvePublicAssetUrl } from "@/lib/seo/public-asset";
import { absoluteUrl, buildPageMetadata } from "@/lib/seo/site";

/** Canonical public Legacy path (middleware also serves `/@username`). */
export function hostLegacyCanonicalPath(username: string): string {
  const slug = username.replace(/^@/, "").trim();
  return `/u/${encodeURIComponent(slug)}`;
}

export function hostLegacyOgImagePath(username: string): string {
  return `${hostLegacyCanonicalPath(username)}/opengraph-image`;
}

export function buildHostMetadata(opts: {
  displayName: string;
  bio?: string | null;
  slug: string;
  image?: string | null;
  category?: string | null;
  location?: string | null;
  noIndex?: boolean;
  ogImageWidth?: number;
  ogImageHeight?: number;
}): Metadata {
  const locationBit = opts.location?.trim();
  const categoryBit = opts.category?.trim();
  const extras = [categoryBit, locationBit].filter(Boolean).join(" · ");
  const description =
    opts.bio?.trim().slice(0, 160) ||
    `${opts.displayName} on Pàdéyá${extras ? ` — ${extras}` : ""} — upcoming events, Memories, and Vault.`;

  return buildPageMetadata({
    title: opts.displayName,
    description,
    path: hostLegacyCanonicalPath(opts.slug),
    image: resolvePublicAssetUrl(opts.image) ?? opts.image,
    ogImageWidth: opts.ogImageWidth,
    ogImageHeight: opts.ogImageHeight,
    noIndex: opts.noIndex,
  });
}

export function buildHostMetadataFromPage(page: LegacyPage): Metadata {
  const bio =
    page.tagline ||
    page.settings?.tagline ||
    page.about ||
    page.profile?.bio ||
    null;
  const category =
    page.settings?.primary_category_slug?.replace(/-/g, " ") ||
    page.settings?.host_type_slug?.replace(/-/g, " ") ||
    null;
  const location =
    [page.profile?.city, page.profile?.state].filter(Boolean).join(", ") ||
    null;

  return buildHostMetadata({
    displayName: page.display_name,
    bio,
    slug: page.username,
    category,
    location,
    // Same-origin DP card from avatar (not cover/logo).
    image: hostLegacyOgImagePath(page.username),
    ogImageWidth: PROFILE_OG_SIZE.width,
    ogImageHeight: PROFILE_OG_SIZE.height,
  });
}

function publicSameAs(page: LegacyPage): string[] {
  const urls: string[] = [];
  const website = page.profile?.website?.trim();
  if (website && /^https?:\/\//i.test(website)) urls.push(website);

  for (const link of page.social_links ?? []) {
    if (!link.is_visible) continue;
    const u = (link.url || "").trim();
    if (u && /^https?:\/\//i.test(u)) urls.push(u);
  }

  const fromProfile = page.profile?.social_links;
  if (fromProfile && typeof fromProfile === "object") {
    for (const value of Object.values(fromProfile)) {
      const u = String(value || "").trim();
      if (u && /^https?:\/\//i.test(u)) urls.push(u);
    }
  }

  return [...new Set(urls)];
}

/** ProfilePage → Organization for public Host Legacy. */
export function hostLegacyJsonLd(page: LegacyPage): Record<string, unknown> {
  const url = absoluteUrl(hostLegacyCanonicalPath(page.username));
  const description =
    page.tagline ||
    page.settings?.tagline ||
    page.about ||
    page.profile?.bio ||
    `${page.display_name} on Pàdéyá`;
  const logo = resolvePublicAssetUrl(page.profile?.avatar_url) || undefined;
  const image =
    resolvePublicAssetUrl(page.profile?.avatar_url) ||
    resolvePublicAssetUrl(page.profile?.cover_url) ||
    logo;
  const sameAs = publicSameAs(page);

  const org: Record<string, unknown> = {
    "@type": "Organization",
    // Host-specific @id — never reuse https://padeya.com/#organization
    "@id": `${url}#organization`,
    name: page.display_name,
    url,
    description: String(description).slice(0, 500),
  };
  if (logo) org.logo = logo;
  if (image) org.image = image;
  if (sameAs.length) org.sameAs = sameAs;

  const city = page.profile?.city?.trim();
  if (city) {
    org.address = {
      "@type": "PostalAddress",
      addressLocality: city,
      addressRegion: page.profile?.state || undefined,
      addressCountry: page.profile?.country || undefined,
    };
  }

  return {
    "@context": "https://schema.org",
    "@type": "ProfilePage",
    name: `${page.display_name} · Host Legacy`,
    url,
    mainEntity: org,
  };
}
