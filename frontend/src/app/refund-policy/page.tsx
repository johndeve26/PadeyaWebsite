import type { Metadata } from "next";

import { LegalDocument } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import {
  RefundPolicyContent,
  REFUND_TOC,
} from "@/lib/legal/refund-policy-content";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Refund Policy",
  description: `Refund rules for tickets, guest checkout, merch, and Vault on ${brand.name}.`,
  path: "/refund-policy",
});

export const revalidate = 3600;

export default function RefundPolicyPage() {
  return (
    <LegalDocument
      title="Refund Policy"
      description={`When refunds are available on ${brand.name}, and how to request them.`}
      toc={REFUND_TOC}
    >
      <RefundPolicyContent />
    </LegalDocument>
  );
}
