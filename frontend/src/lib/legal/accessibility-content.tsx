import Link from "next/link";

import { LegalSection } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import {
  PLATFORM_RELATIONSHIP_TOC,
  PlatformRelationshipSection,
} from "@/lib/legal/platform-relationship";
import { legalToc } from "@/lib/legal/toc";

export const ACCESSIBILITY_TOC = legalToc(
  { id: "commitment", title: "Our commitment" },
  PLATFORM_RELATIONSHIP_TOC,
  { id: "website", title: "Website & product accessibility" },
  { id: "events", title: "Event accessibility" },
  { id: "hosts", title: "Guidance for hosts" },
  { id: "help", title: "Getting help" },
);

export function AccessibilityContent() {
  return (
    <>
      <LegalSection id="commitment" title="Our commitment">
        <p>
          {brand.name} aims to make discovery, checkout, tickets, and account
          tools usable across devices — with readable typography, keyboard focus
          states, semantic structure, and sufficient contrast, including dark
          mode. We improve accessibility continuously based on real product use
          and feedback.
        </p>
      </LegalSection>

      <PlatformRelationshipSection />

      <LegalSection id="website" title="Website & product accessibility">
        <ul>
          <li>Semantic headings and labeled form controls on key flows</li>
          <li>Mobile-first layouts for checkout and door-ready tickets</li>
          <li>High-contrast presentation for critical ticket information where possible</li>
          <li>Focus-visible states for interactive controls</li>
        </ul>
        <p>
          Accessibility of the Platform does not guarantee that every third-party
          venue or host space meets the same standard.
        </p>
      </LegalSection>

      <LegalSection id="events" title="Event accessibility">
        <p>
          Physical and on-site accessibility (ramps, seating, restrooms, sensory
          considerations, entry assistance) depends on the host and venue.{" "}
          {brand.name} is not the venue operator for third-party host events
          unless expressly stated.
        </p>
        <p>
          Review listing details before purchase, and contact the host when you
          need specific arrangements.
        </p>
      </LegalSection>

      <LegalSection id="hosts" title="Guidance for hosts">
        <p>
          Hosts should provide accurate accessibility information in listings
          when possible, plan for disclosed needs, and communicate entry
          constraints clearly. Misrepresenting access can violate our{" "}
          <Link href="/community-guidelines">Community Guidelines</Link>.
        </p>
      </LegalSection>

      <LegalSection id="help" title="Getting help">
        <p>
          If you hit a barrier on the website or app, open a{" "}
          <Link href="/support/new?category=technical">Support</Link> ticket
          under a technical category and describe the page, device, and assistive
          technology you use. For event-specific needs, message the host where
          messaging is available, or contact{" "}
          <Link href="/contact">Contact</Link>.
        </p>
      </LegalSection>
    </>
  );
}
