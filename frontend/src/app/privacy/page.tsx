import type { Metadata } from "next";

import { LegalDocument } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import { PrivacyContent, PRIVACY_TOC } from "@/lib/legal/privacy-content";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Privacy Policy",
  description: `How ${brand.name} collects and uses account, checkout, ticket, Fan Passport, Fan Connect, and support data.`,
  path: "/privacy",
});

export const revalidate = 3600;

export default function PrivacyPage() {
  return (
    <LegalDocument
      title="Privacy Policy"
      description={`How ${brand.name} handles personal information for fans, hosts, guests, and visitors.`}
      toc={PRIVACY_TOC}
    >
      <PrivacyContent />
    </LegalDocument>
  );
}
