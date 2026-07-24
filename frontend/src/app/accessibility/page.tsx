import type { Metadata } from "next";

import { LegalDocument } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import {
  AccessibilityContent,
  ACCESSIBILITY_TOC,
} from "@/lib/legal/accessibility-content";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Accessibility",
  description: `Accessibility statement for ${brand.name}: product commitment, event venue limits, and how to get help.`,
  path: "/accessibility",
});

export const revalidate = 3600;

export default function AccessibilityPage() {
  return (
    <LegalDocument
      title="Accessibility statement"
      description={`How ${brand.name} approaches accessible product design — and how event access depends on hosts and venues.`}
      toc={ACCESSIBILITY_TOC}
    >
      <AccessibilityContent />
    </LegalDocument>
  );
}
