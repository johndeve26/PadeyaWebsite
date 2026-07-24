import type { Metadata } from "next";

import { MerchView } from "@/components/marketing/merch/MerchView";
import {
  merchFaqs,
  merchGuideSeo,
} from "@/components/marketing/merch/content";
import { faqPageJsonLd } from "@/lib/seo/audience-metadata";
import { breadcrumbJsonLd, JsonLdScript } from "@/lib/seo/jsonld";
import { buildPageMetadata, siteOrigin } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: merchGuideSeo.title,
  description: merchGuideSeo.description,
  path: merchGuideSeo.path,
});

export const revalidate = 3600;

export default function MerchGuidePage() {
  const origin = siteOrigin();

  return (
    <>
      <JsonLdScript data={faqPageJsonLd(merchFaqs, merchGuideSeo.path)} />
      <JsonLdScript
        data={breadcrumbJsonLd(
          [
            { label: "Home", href: "/" },
            { label: "Merch guide", href: merchGuideSeo.path },
          ],
          origin,
        )}
      />
      <MerchView />
    </>
  );
}
