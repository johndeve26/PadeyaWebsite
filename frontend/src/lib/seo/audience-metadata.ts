import type { MarketingFaqItem } from "@/components/marketing/MarketingFaq";
import { absoluteUrl, buildPageMetadata } from "@/lib/seo/site";
import { websiteIdRef } from "@/lib/seo/site-graph";

export function faqPageJsonLd(
  items: readonly MarketingFaqItem[],
  path: string,
): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.a,
      },
    })),
    url: absoluteUrl(path),
    isPartOf: websiteIdRef(),
  };
}

export { buildPageMetadata };
