import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { SponsorProfileClient } from "./SponsorProfileClient";
import { getPublicSponsorBySlug } from "@/lib/public-loaders/entities";
import {
  buildSponsorMetadata,
  sponsorProfileJsonLd,
} from "@/lib/seo/sponsor-metadata";
import { breadcrumbJsonLd, JsonLdScript } from "@/lib/seo/jsonld";
import { siteOrigin } from "@/lib/seo/site";
import { SPONSORSHIP_MARKETPLACE_PATH } from "@/lib/sponsor-marketplace-paths";

export const revalidate = 120;

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const profile = await getPublicSponsorBySlug(slug);
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
  const profile = await getPublicSponsorBySlug(slug);
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
