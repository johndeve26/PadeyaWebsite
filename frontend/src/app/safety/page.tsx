import type { Metadata } from "next";
import Link from "next/link";

import { LegalToc } from "@/components/legal/LegalDocument";
import {
  PublicCtaPair,
  PublicPageShell,
} from "@/components/marketing/PublicPageShell";
import { brand } from "@/lib/brand";
import { SafetyContent, SAFETY_TOC } from "@/lib/legal/safety-content";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Safety Center",
  description: `Safety tips for buying, attending, verifying tickets, reporting abuse, and emergencies on ${brand.name}.`,
  path: "/safety",
});

export const revalidate = 3600;

export default function SafetyPage() {
  return (
    <PublicPageShell
      eyebrow="Trust & safety"
      title="Safety Center"
      description={`${brand.name} builds for verified access and clearer accountability. Use this guide to buy, attend, and report more safely.`}
      actions={
        <PublicCtaPair
          primaryHref="/report"
          primaryLabel="Report an issue"
          secondaryHref="/support"
          secondaryLabel="Support Center"
        />
      }
      narrow
    >
      <div className="mx-auto max-w-3xl space-y-8">
        <LegalToc items={SAFETY_TOC} />
        <article className="prose prose-neutral dark:prose-invert max-w-none space-y-10 text-base leading-relaxed text-foreground prose-headings:font-display prose-headings:text-heading prose-a:text-primary">
          <SafetyContent />
        </article>
        <p className="border-t border-border pt-6 text-sm text-muted-foreground">
          Also read our{" "}
          <Link href="/community-guidelines" className="font-semibold text-primary">
            Community Guidelines
          </Link>{" "}
          and{" "}
          <Link href="/ticket-policy" className="font-semibold text-primary">
            Ticket Policy
          </Link>
          .
        </p>
      </div>
    </PublicPageShell>
  );
}
