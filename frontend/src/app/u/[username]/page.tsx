import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { LegacyPublicClient } from "./LegacyPublicClient";
import {
  buildHostMetadataFromPage,
  hostLegacyCanonicalPath,
  hostLegacyJsonLd,
} from "@/lib/seo/host-metadata";
import { breadcrumbJsonLd, JsonLdScript } from "@/lib/seo/jsonld";
import { fetchPublicJson } from "@/lib/seo/public-fetch";
import { siteOrigin } from "@/lib/seo/site";
import type { LegacyPage } from "@/lib/types/legacy";

export const revalidate = 120;

async function loadLegacyPage(username: string): Promise<LegacyPage | null> {
  const { data, status } = await fetchPublicJson<LegacyPage>(
    `/u/${encodeURIComponent(username)}/legacy`,
    { revalidate: 120 },
  );
  if (status === 404 || !data) return null;
  // Inactive / non-active hosts must not be indexed as live Legacy pages.
  if (data.status && data.status !== "active") return null;
  return data;
}

type Props = { params: Promise<{ username: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { username } = await params;
  const decoded = decodeURIComponent(username);
  const page = await loadLegacyPage(decoded);
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
  const page = await loadLegacyPage(decoded);
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
