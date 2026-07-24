import type { MarketingFaqItem } from "@/components/marketing/MarketingFaq";
import { brand } from "@/lib/brand";
import { absoluteUrl, buildPageMetadata, siteOrigin } from "@/lib/seo/site";

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
    isPartOf: {
      "@type": "WebSite",
      name: brand.name,
      url: siteOrigin(),
    },
  };
}

export { buildPageMetadata };
