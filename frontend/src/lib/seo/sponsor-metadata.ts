import type { Metadata } from "next";

import type { SponsorPublicProfile } from "@/lib/sponsor-profiles-api";
import { pickEntityOgImage, resolvePublicAssetUrl } from "@/lib/seo/public-asset";
import { absoluteUrl, buildPageMetadata } from "@/lib/seo/site";
import { sponsorBrandProfilePath } from "@/lib/sponsor-marketplace-paths";

export function buildSponsorMetadata(
  profile: SponsorPublicProfile,
): Metadata {
  const industry = profile.industry?.replace(/_/g, " ");
  const categories = (profile.categories || [])
    .slice(0, 3)
    .map((c) => c.replace(/_/g, " "));
  const locations = (profile.target_locations || []).slice(0, 3);
  const bits = [industry, ...categories, ...locations].filter(Boolean);
  const description =
    profile.short_bio?.trim().slice(0, 160) ||
    profile.description?.trim().slice(0, 160) ||
    profile.partnership_blurb?.trim().slice(0, 160) ||
    `${profile.display_name} on Pàdéyá${bits.length ? ` — ${bits.join(" · ")}` : ""} — brand partnerships and sponsored events.`;

  const image = pickEntityOgImage({
    cover: profile.cover_image_url,
    logo: profile.logo_url,
  });

  return buildPageMetadata({
    title: profile.display_name,
    description,
    path: sponsorBrandProfilePath(profile.slug),
    image,
  });
}

export function sponsorProfileJsonLd(
  profile: SponsorPublicProfile,
): Record<string, unknown> {
  const url = absoluteUrl(sponsorBrandProfilePath(profile.slug));
  const description =
    profile.short_bio ||
    profile.description ||
    profile.partnership_blurb ||
    `${profile.display_name} on Pàdéyá`;
  const logo = resolvePublicAssetUrl(profile.logo_url) || undefined;
  const image =
    resolvePublicAssetUrl(profile.cover_image_url) || logo || undefined;
  const sameAs: string[] = [];
  if (profile.website_url && /^https?:\/\//i.test(profile.website_url)) {
    sameAs.push(profile.website_url);
  }

  const org: Record<string, unknown> = {
    "@type": "Organization",
    // Sponsor-specific @id — never reuse https://padeya.com/#organization
    "@id": `${url}#organization`,
    name: profile.display_name,
    url,
    description: String(description).slice(0, 500),
  };
  if (logo) org.logo = logo;
  if (image) org.image = image;
  if (sameAs.length) org.sameAs = sameAs;
  if (profile.industry) {
    org.knowsAbout = profile.industry.replace(/_/g, " ");
  }
  if (profile.categories?.length) {
    org.category = profile.categories.map((c) => c.replace(/_/g, " "));
  }
  const loc = profile.target_locations?.[0];
  if (loc) {
    org.areaServed = loc.replace(/_/g, " ");
  }

  return {
    "@context": "https://schema.org",
    "@type": "ProfilePage",
    name: `${profile.display_name} · Sponsor`,
    url,
    mainEntity: org,
  };
}

export function sponsorshipsIndexMetadata(): Metadata {
  return buildPageMetadata({
    title: "Sponsorships",
    description:
      "Discover open sponsorship slots and partner with verified Pàdéyá hosts — brand placements, event activations, and measurable nightlife audiences.",
    path: "/sponsorships",
  });
}

export function sponsorshipHostsIndexMetadata(): Metadata {
  return buildPageMetadata({
    title: "Hosts open to sponsorship",
    description:
      "Browse verified Pàdéyá hosts with event history, checked-in attendance, Legacy reputation, and open sponsorship slots.",
    path: "/sponsorships/hosts",
  });
}
