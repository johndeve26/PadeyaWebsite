import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { LegacyPublicClient } from "./LegacyPublicClient";
import { getPublicLegacyByUsername } from "@/lib/public-loaders/entities";
import {
  buildHostMetadataFromPage,
  hostLegacyCanonicalPath,
  hostLegacyJsonLd,
} from "@/lib/seo/host-metadata";
import { breadcrumbJsonLd, JsonLdScript } from "@/lib/seo/jsonld";
import { siteOrigin } from "@/lib/seo/site";

export const revalidate = 120;

type Props = { params: Promise<{ username: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { username } = await params;
  const decoded = decodeURIComponent(username);
  const page = await getPublicLegacyByUsername(decoded);
  if (!page) {
    return { title: "Host", robots: { index: false, follow: false } };
  }
  return buildHostMetadataFromPage(page);
}

/**
 * Public host Legacy Page (also reachable via `/@username` rewrite).
 * Missing / inactive hosts → HTTP 404 (privacy by omission).
 */
export default async function PublicLegacyUsernamePage({ params }: Props) {
  const { username } = await params;
  const decoded = decodeURIComponent(username);
  const page = await getPublicLegacyByUsername(decoded);
  if (!page) notFound();

  const crumbs = [
    { label: "Home", href: "/" },
    { label: "Hosts", href: "/hosts" },
    { label: page.display_name, href: hostLegacyCanonicalPath(page.username) },
  ];

  return (
    <>
      <JsonLdScript data={hostLegacyJsonLd(page)} />
      <JsonLdScript data={breadcrumbJsonLd(crumbs, siteOrigin())} />
      <LegacyPublicClient page={page} />
    </>
  );
}
