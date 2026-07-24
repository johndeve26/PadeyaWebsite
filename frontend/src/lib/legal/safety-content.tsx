import Link from "next/link";

import { LegalSection } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import {
  PLATFORM_RELATIONSHIP_TOC,
  PlatformRelationshipSection,
} from "@/lib/legal/platform-relationship";
import { legalToc } from "@/lib/legal/toc";

export const SAFETY_TOC = legalToc(
  { id: "buying-safely", title: "Buying safely" },
  PLATFORM_RELATIONSHIP_TOC,
  { id: "attending", title: "Attending safely" },
  { id: "verify-ticket", title: "Verifying tickets & QR" },
  { id: "location-privacy", title: "Event location privacy" },
  { id: "reporting", title: "Reporting abuse" },
  { id: "block-report", title: "Block & report controls" },
  { id: "host-safety", title: "Host safety responsibility" },
  { id: "suspicious", title: "Suspicious listings" },
  { id: "escalation", title: "Support escalation" },
  { id: "emergencies", title: "Emergencies" },
);

export function SafetyContent() {
  return (
    <>
      <LegalSection id="buying-safely" title="Buying safely">
        <ul>
          <li>
            Prefer checkout on {brand.name} so orders, tickets, and disputes have
            a clear trail.
          </li>
          <li>
            Be cautious with off-platform payment requests, “too good to be true”
            resales, or anyone asking for OTPs.
          </li>
          <li>
            Review age rules, fees, and host policies before you pay. See the{" "}
            <Link href="/ticket-policy">Ticket Policy</Link> and{" "}
            <Link href="/refund-policy">Refund Policy</Link>.
          </li>
        </ul>
      </LegalSection>

      <PlatformRelationshipSection />

      <LegalSection id="attending" title="Attending safely">
        <ul>
          <li>Travel with a plan and share your whereabouts with someone you trust when helpful.</li>
          <li>Follow venue security and host entry instructions.</li>
          <li>Leave if a situation feels unsafe — your wellbeing comes first.</li>
        </ul>
      </LegalSection>

      <LegalSection id="verify-ticket" title="Verifying tickets & QR">
        <p>
          Trust tickets issued in your {brand.name} account or official claim
          flow. If a QR fails, ask staff to rescan with host tools — do not hand
          OTPs or payment secrets to strangers. Checked-in codes are not for
          reuse.
        </p>
      </LegalSection>

      <LegalSection id="location-privacy" title="Event location privacy">
        <p>
          Some hosts reveal precise addresses only after purchase. That protects
          venues and attendees from drive-by abuse. Do not publicly post private
          streets or join links you received as a buyer.
        </p>
      </LegalSection>

      <LegalSection id="reporting" title="Reporting abuse">
        <p>
          Report harassment, fraud, unsafe listings, impersonation, or payment
          issues through <Link href="/report">Report</Link> or{" "}
          <Link href="/support">Support</Link>. Include usernames, links, and
          order references — never passwords, full card numbers, or QR secrets.
        </p>
      </LegalSection>

      <LegalSection id="block-report" title="Block & report controls">
        <p>
          Fan Connect and messaging include block and report tools. Blocking
          limits that person’s ability to reach you according to product rules.
          Reports are reviewed by authorized staff; internal notes stay internal.
        </p>
      </LegalSection>

      <LegalSection id="host-safety" title="Host safety responsibility">
        <p>
          Hosts are responsible for venue readiness, permits, crowd control, age
          restrictions, accessibility arrangements, and emergency planning for
          their events. {brand.name} may moderate listings that create platform
          risk, but hosts remain the on-site organizers for third-party events.
        </p>
      </LegalSection>

      <LegalSection id="suspicious" title="Suspicious listings">
        <p>
          Warning signs include pressure to pay outside {brand.name}, copied
          branding, impossible pricing, or hosts refusing basic entry
          information after purchase. Report the listing and avoid off-platform
          payment.
        </p>
      </LegalSection>

      <LegalSection id="escalation" title="Support escalation">
        <p>
          Start at <Link href="/support">Support</Link> for tracked help. Safety
          and fraud categories are routed for faster review. Account restrictions
          can be appealed at{" "}
          <Link href="/account/appeal">Account appeal</Link> when available.
        </p>
      </LegalSection>

      <LegalSection id="emergencies" title="Emergencies">
        <p>
          If you or someone else is in immediate danger, contact local emergency
          services first. After you are safe,{" "}
          <Link href="/report">report on {brand.name}</Link> so we can review
          platform-related risk.
        </p>
      </LegalSection>
    </>
  );
}
