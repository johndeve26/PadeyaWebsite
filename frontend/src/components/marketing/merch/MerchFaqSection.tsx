import Link from "next/link";

import { MarketingFaq } from "@/components/marketing/MarketingFaq";
import { Container } from "@/components/ui";

import { merchFaqs } from "./content";

const TOP_FAQ_COUNT = 5;

export function MerchFaqSection() {
  const topFaqs = merchFaqs.slice(0, TOP_FAQ_COUNT);

  return (
    <section
      id="merch-faq"
      aria-labelledby="merch-faq-heading"
      className="border-t border-border bg-muted/30 py-12 sm:py-14"
    >
      <Container className="max-w-3xl space-y-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">
            FAQ
          </p>
          <h2
            id="merch-faq-heading"
            className="mt-2 text-2xl font-extrabold tracking-tight text-heading"
          >
            Merch questions
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Add-ons, drops, Vault, pickup, and refunds: the essentials.
          </p>
        </div>
        <MarketingFaq items={topFaqs} />
        <p className="text-sm text-muted-foreground">
          <Link
            href="/faq"
            className="font-semibold text-primary-text hover:underline"
          >
            View all FAQs
          </Link>
          {" · "}
          <Link
            href="/help"
            className="font-semibold text-primary-text hover:underline"
          >
            Help Center
          </Link>
        </p>
      </Container>
    </section>
  );
}
