import type { Metadata } from "next";

import { LegalDocument } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import { TermsContent, TERMS_TOC } from "@/lib/legal/terms-content";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Terms of Service",
  description: `Terms of Service for ${brand.name}: accounts, tickets, hosts, Fan Connect, Ambassadors, sponsorships, and marketplace rules.`,
  path: "/terms",
});

export const revalidate = 3600;

export default function TermsPage() {
  return (
    <LegalDocument
      title="Terms of Service"
      description={`The rules for using ${brand.name} as a fan, host, buyer, ambassador, or visitor.`}
      toc={TERMS_TOC}
    >
      <TermsContent />
    </LegalDocument>
  );
}
