import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { FanPassportPublicClient } from "@/components/passport/FanPassportPublicClient";
import {
  buildFanMetadata,
  fanPassportCanonicalPath,
  fanPassportJsonLd,
  isFanPassportIndexable,
} from "@/lib/seo/fan-metadata";
import { breadcrumbJsonLd, JsonLdScript } from "@/lib/seo/jsonld";
import { fetchPublicJson } from "@/lib/seo/public-fetch";
import { NOINDEX_ROBOTS } from "@/lib/seo/noindex";
import { siteOrigin } from "@/lib/seo/site";
import type { FanPassportPublicPage } from "@/lib/types/passport";

async function loadPublicPassport(
  username: string,
): Promise<FanPassportPublicPage | null> {
  const { data, status } = await fetchPublicJson<FanPassportPublicPage>(
    `/f/${encodeURIComponent(username)}`,
    { revalidate: false },
  );
  if (status === 404 || !data) return null;
  return data;
}

type Props = { params: Promise<{ username: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { username } = await params;
  const page = await loadPublicPassport(decodeURIComponent(username));
  if (!page) {
    return { title: "Fan Passport", robots: NOINDEX_ROBOTS };
  }
  return buildFanMetadata(page);
}

export default async function PublicFanPassportPage({ params }: Props) {
  const { username } = await params;
  const page = await loadPublicPassport(decodeURIComponent(username));
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
