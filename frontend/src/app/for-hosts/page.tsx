import type { Metadata } from "next";

import { ForHostsView } from "@/components/marketing/for-hosts/ForHostsView";
import {
  forHostsFaqs,
  forHostsSeo,
} from "@/components/marketing/for-hosts/content";
import { faqPageJsonLd } from "@/lib/seo/audience-metadata";
import { breadcrumbJsonLd, JsonLdScript } from "@/lib/seo/jsonld";
import { buildPageMetadata, siteOrigin } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: forHostsSeo.title,
  description: forHostsSeo.description,
  path: forHostsSeo.path,
});

export const revalidate = 3600;

export default function ForHostsPage() {
  const origin = siteOrigin();

  return (
    <>
      <JsonLdScript data={faqPageJsonLd(forHostsFaqs, forHostsSeo.path)} />
      <JsonLdScript
        data={breadcrumbJsonLd(
          [
            { label: "Home", href: "/" },
            { label: "For hosts", href: forHostsSeo.path },
          ],
          origin,
        )}
      />
      <ForHostsView />
    </>
  );
}
