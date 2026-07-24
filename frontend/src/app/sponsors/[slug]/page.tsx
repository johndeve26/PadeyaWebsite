import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { SponsorProfileClient } from "./SponsorProfileClient";
import {
  buildSponsorMetadata,
  sponsorProfileJsonLd,
} from "@/lib/seo/sponsor-metadata";
import { breadcrumbJsonLd, JsonLdScript } from "@/lib/seo/jsonld";
import { fetchPublicJson } from "@/lib/seo/public-fetch";
import { siteOrigin } from "@/lib/seo/site";
import { SPONSORSHIP_MARKETPLACE_PATH } from "@/lib/sponsor-marketplace-paths";
import type { SponsorPublicProfile } from "@/lib/sponsor-profiles-api";

export const revalidate = 120;

async function loadSponsorProfile(
  slug: string,
): Promise<SponsorPublicProfile | null> {
  const { data, status } = await fetchPublicJson<SponsorPublicProfile>(
    `/sponsors/public/${encodeURIComponent(slug)}`,
    { revalidate: 120 },
  );
  if (status === 404 || !data) return null;
  return data;
}

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const profile = await loadSponsorProfile(slug);
  if (!profile) {
    return { title: "Sponsor", robots: { index: false, follow: false } };
  }
  return buildSponsorMetadata(profile);
}

/**
 * Public verified sponsor brand profile.
 * Missing / private / ineligible → HTTP 404 (no soft Alert).
 */
export default async function PublicSponsorProfilePage({ params }: Props) {
  const { slug } = await params;
  const profile = await loadSponsorProfile(slug);
  if (!profile) notFound();

  const crumbs = [
    { label: "Home", href: "/" },
    { label: "Sponsorships", href: SPONSORSHIP_MARKETPLACE_PATH },
    { label: profile.display_name },
  ];

  return (
    <>
      <JsonLdScript data={sponsorProfileJsonLd(profile)} />
      <JsonLdScript data={breadcrumbJsonLd(crumbs, siteOrigin())} />
      <SponsorProfileClient profile={profile} />
    </>
  );
}
