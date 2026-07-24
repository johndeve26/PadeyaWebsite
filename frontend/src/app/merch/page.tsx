import type { Metadata } from "next";
import { Suspense } from "react";

import { MerchMarketplaceView } from "@/components/merch/marketplace/MerchMarketplaceView";
import { merchFaqs, merchSeo } from "@/components/marketing/merch/content";
import { faqPageJsonLd } from "@/lib/seo/audience-metadata";
import { breadcrumbJsonLd, JsonLdScript } from "@/lib/seo/jsonld";
import { buildPageMetadata, siteOrigin } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: merchSeo.title,
  description: merchSeo.description,
  path: merchSeo.path,
});

export default function MerchPage() {
  const origin = siteOrigin();

  return (
    <>
      <JsonLdScript data={faqPageJsonLd(merchFaqs, merchSeo.path)} />
      <JsonLdScript
        data={breadcrumbJsonLd(
          [
            { label: "Home", href: "/" },
            { label: "Merch", href: merchSeo.path },
          ],
          origin,
        )}
      />
      <Suspense fallback={null}>
        <MerchMarketplaceView />
      </Suspense>
    </>
  );
}
