import type { Metadata } from "next";

import { LegalToc } from "@/components/legal/LegalDocument";
import {
  PublicCtaPair,
  PublicPageShell,
} from "@/components/marketing/PublicPageShell";
import { brand } from "@/lib/brand";
import { ReportContent, REPORT_TOC } from "@/lib/legal/report-content";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Report an issue",
  description: `Report events, hosts, users, messages, payments, safety concerns, or fraud on ${brand.name}.`,
  path: "/report",
});

export default function ReportPage() {
  return (
    <PublicPageShell
      eyebrow="Trust & safety"
      title="Report an issue"
      description={`File a tracked report so ${brand.name} can route abuse, fraud, safety, and order concerns quickly.`}
      actions={
        <PublicCtaPair
          primaryHref="/support/new?category=messaging_abuse"
          primaryLabel="Start a report"
          secondaryHref="/safety"
          secondaryLabel="Safety Center"
        />
      }
      narrow
    >
      <div className="mx-auto max-w-3xl space-y-8">
        <LegalToc items={REPORT_TOC} />
        <article className="prose prose-neutral dark:prose-invert max-w-none space-y-10 text-base leading-relaxed text-foreground prose-headings:font-display prose-headings:text-heading prose-a:text-primary">
          <ReportContent />
        </article>
      </div>
    </PublicPageShell>
  );
}
