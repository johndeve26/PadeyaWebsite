import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { FanPassportPublicClient } from "@/components/passport/FanPassportPublicClient";
import { getPublicFanPassport } from "@/lib/public-loaders/entities";
import {
  buildFanMetadata,
  fanPassportCanonicalPath,
  fanPassportJsonLd,
  isFanPassportIndexable,
} from "@/lib/seo/fan-metadata";
import { breadcrumbJsonLd, JsonLdScript } from "@/lib/seo/jsonld";
import { NOINDEX_ROBOTS } from "@/lib/seo/noindex";
import { siteOrigin } from "@/lib/seo/site";

/**
 * Fan Passport public HTML is intentionally **not** CDN/ISR cached.
 *
 * Privacy invariant: PUBLIC/UNLISTED → PRIVATE must not leave stale HTML
 * on Vercel. React `cache()` still dedupes metadata + page within one request.
 *
 * Directory (`/fans`) remains short-ISR and is purged via the authenticated
 * `/api/revalidate/fan` route when visibility changes.
 */
export const dynamic = "force-dynamic";
export const revalidate = 0;

type Props = { params: Promise<{ username: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { username } = await params;
  const page = await getPublicFanPassport(decodeURIComponent(username));
  if (!page) {
    return { title: "Fan Passport", robots: NOINDEX_ROBOTS };
  }
  return buildFanMetadata(page);
}

export default async function PublicFanPassportPage({ params }: Props) {
  const { username } = await params;
  const page = await getPublicFanPassport(decodeURIComponent(username));
  if (!page) notFound();

  const schema = fanPassportJsonLd(page);
  const crumbs = isFanPassportIndexable(page)
    ? [
        { label: "Home", href: "/" },
        { label: "Fans", href: "/fans" },
        {
          label: page.display_name,
          href: fanPassportCanonicalPath(page.username),
        },
      ]
    : null;

  return (
    <>
      {schema ? <JsonLdScript data={schema} /> : null}
      {crumbs ? (
        <JsonLdScript data={breadcrumbJsonLd(crumbs, siteOrigin())} />
      ) : null}
      <FanPassportPublicClient initial={page} />
    </>
  );
}
