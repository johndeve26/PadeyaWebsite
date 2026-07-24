import type { Metadata } from "next";

import { LegalDocument } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import {
  TicketPolicyContent,
  TICKET_TOC,
} from "@/lib/legal/ticket-policy-content";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Ticket Policy",
  description: `Ticket ownership, QR issuance, transfers, check-in, and entry rules on ${brand.name}.`,
  path: "/ticket-policy",
});

export const revalidate = 3600;

export default function TicketPolicyPage() {
  return (
    <LegalDocument
      title="Ticket Policy"
      description={`How tickets work on ${brand.name} — from verified payment to door scan.`}
      toc={TICKET_TOC}
    >
      <TicketPolicyContent />
    </LegalDocument>
  );
}
