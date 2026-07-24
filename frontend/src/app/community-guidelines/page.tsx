import type { Metadata } from "next";

import { LegalDocument } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import {
  CommunityGuidelinesContent,
  COMMUNITY_TOC,
} from "@/lib/legal/community-guidelines-content";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Community Guidelines",
  description: `Community standards for fans, hosts, ambassadors, and messaging on ${brand.name}.`,
  path: "/community-guidelines",
});

export const revalidate = 3600;

export default function CommunityGuidelinesPage() {
  return (
    <LegalDocument
      title="Community Guidelines"
      description={`How we expect people to show up on ${brand.name}.`}
      toc={COMMUNITY_TOC}
    >
      <CommunityGuidelinesContent />
    </LegalDocument>
  );
}
