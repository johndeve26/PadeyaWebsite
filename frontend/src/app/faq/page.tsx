import type { Metadata } from "next";

import { FaqExplorer } from "@/components/faq/FaqExplorer";
import { FaqStillNeedHelp } from "@/components/faq/FaqStillNeedHelp";
import { Container } from "@/components/ui";
import { brand } from "@/lib/brand";
import {
  allFaqItems,
  FAQ_CATEGORIES,
  FAQ_SEO,
  faqAnswerPlainText,
} from "@/lib/faq/faq-content";
import { faqPageJsonLd } from "@/lib/seo/audience-metadata";
import { JsonLdScript } from "@/lib/seo/jsonld";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: FAQ_SEO.title,
  description: FAQ_SEO.description,
  path: FAQ_SEO.path,
});

export const revalidate = 3600;

export default function FaqPage() {
  const jsonLdItems = allFaqItems().map((item) => ({
    q: item.q,
    a: faqAnswerPlainText(item.a),
  }));

  return (
    <>
      <JsonLdScript data={faqPageJsonLd(jsonLdItems, FAQ_SEO.path)} />
      <main className="relative overflow-hidden bg-background pb-20 pt-10 text-foreground sm:pt-14">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_color-mix(in_srgb,var(--primary)_14%,transparent),_transparent_55%),linear-gradient(180deg,var(--surface-muted),var(--background))]"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[28rem] bg-[linear-gradient(135deg,transparent_40%,color-mix(in_srgb,var(--primary)_8%,transparent)_100%)]"
        />

        <Container>
          <header className="mx-auto max-w-3xl text-center">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-text">
              {brand.name} FAQ
            </p>
            <h1 className="mt-3 font-display text-4xl font-extrabold tracking-tight text-heading sm:text-5xl">
              Answers before the night starts
            </h1>
            <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
              Tickets, guest checkout, Fan Passport, hosting, check-in, merch,
              Ambassadors, sponsorships, refunds, and support — search or jump
              to a category.
            </p>
          </header>

          <div className="mt-10 sm:mt-12">
            <FaqExplorer categories={FAQ_CATEGORIES} />
          </div>

          <div className="mt-16 sm:mt-20">
            <FaqStillNeedHelp />
          </div>
        </Container>
      </main>
    </>
  );
}
