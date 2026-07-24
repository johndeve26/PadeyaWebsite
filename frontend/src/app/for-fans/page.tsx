import type { Metadata } from "next";

import { ForFansView } from "@/components/marketing/for-fans/ForFansView";
import {
  forFansFaqs,
  forFansSeo,
} from "@/components/marketing/for-fans/content";
import { faqPageJsonLd } from "@/lib/seo/audience-metadata";
import { breadcrumbJsonLd, JsonLdScript } from "@/lib/seo/jsonld";
import { buildPageMetadata, siteOrigin } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: forFansSeo.title,
  description: forFansSeo.description,
  path: forFansSeo.path,
});

export const revalidate = 3600;

export default function ForFansPage() {
  const origin = siteOrigin();

  return (
    <>
      <JsonLdScript data={faqPageJsonLd(forFansFaqs, forFansSeo.path)} />
      <JsonLdScript
        data={breadcrumbJsonLd(
          [
            { label: "Home", href: "/" },
            { label: "For fans", href: forFansSeo.path },
          ],
          origin,
        )}
      />
      <ForFansView />
    </>
  );
}
