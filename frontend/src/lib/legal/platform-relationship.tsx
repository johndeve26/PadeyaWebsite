import Link from "next/link";

import { brand } from "@/lib/brand";

import { LegalSection } from "@/components/legal/LegalDocument";

export const PLATFORM_RELATIONSHIP_TOC = {
  id: "platform-relationship",
  title: "Platform relationship",
} as const;

/**
 * Shared marketplace / host / buyer relationship language for trust pages.
 * Keep claims measured — no insurance or compliance overpromises.
 */
export function PlatformRelationshipSection({
  showRelatedLinks = true,
}: {
  showRelatedLinks?: boolean;
} = {}) {
  return (
    <LegalSection id={PLATFORM_RELATIONSHIP_TOC.id} title={PLATFORM_RELATIONSHIP_TOC.title}>
      <p>
        {brand.name} is a technology platform and marketplace for event discovery,
        ticketing, host tools, fan identity, support, and related services.
      </p>
      <p>Unless expressly stated otherwise:</p>
      <ul>
        <li>
          {brand.name} is not the organizer, host, promoter, venue, performer,
          sponsor, security provider, transport provider, or food/drink provider
          for events listed by third-party hosts.
        </li>
        <li>
          Hosts are independent organizers. They are responsible for listing
          accuracy, event safety, venue readiness, permits, crowd control, age
          restrictions, accessibility arrangements, emergency planning, and
          compliance with applicable rules.
        </li>
        <li>
          Hosts are responsible for communicating event changes, cancellations,
          entry rules, venue rules, and refund terms where those apply to their
          events.
        </li>
        <li>
          Fans and buyers are responsible for reviewing event details, policies,
          and requirements before purchasing or attending.
        </li>
        <li>
          {brand.name} may moderate, restrict, remove, or suspend listings or
          accounts where safety, fraud, abuse, legal, or platform-risk concerns
          arise.
        </li>
      </ul>
      {showRelatedLinks ? (
        <p>
          Related:{" "}
          <Link href="/terms">Terms</Link>, <Link href="/ticket-policy">Ticket Policy</Link>,{" "}
          <Link href="/refund-policy">Refund Policy</Link>,{" "}
          <Link href="/safety">Safety</Link>, and{" "}
          <Link href="/community-guidelines">Community Guidelines</Link>.
        </p>
      ) : null}
    </LegalSection>
  );
}
