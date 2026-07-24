import Link from "next/link";

import { LegalSection } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import {
  PLATFORM_RELATIONSHIP_TOC,
  PlatformRelationshipSection,
} from "@/lib/legal/platform-relationship";
import { legalToc } from "@/lib/legal/toc";

export const COMMUNITY_TOC = legalToc(
  { id: "respect", title: "Respectful behavior" },
  PLATFORM_RELATIONSHIP_TOC,
  { id: "harassment", title: "Harassment & abuse" },
  { id: "scams", title: "Scams & fraud" },
  { id: "impersonation", title: "Impersonation" },
  { id: "unsafe-events", title: "Unsafe events" },
  { id: "prohibited-content", title: "Prohibited content" },
  { id: "fan-connect", title: "Fan Connect behavior" },
  { id: "messaging", title: "Messaging rules" },
  { id: "reviews", title: "Review rules" },
  { id: "ambassadors", title: "Ambassador conduct" },
  { id: "hosts", title: "Host conduct" },
  { id: "enforcement", title: "Enforcement" },
);

export function CommunityGuidelinesContent() {
  return (
    <>
      <LegalSection id="respect" title="Respectful behavior">
        <p>
          {brand.name} is built for nights people can trust — discovery,
          ticketing, hosting, and fan connection. Treat other fans, hosts,
          ambassadors, sponsors, and staff with respect. Disagreements happen;
          abuse does not belong here.
        </p>
      </LegalSection>

      <PlatformRelationshipSection />

      <LegalSection id="harassment" title="Harassment & abuse">
        <ul>
          <li>No threats, hate, stalking, or unwanted sexual content.</li>
          <li>No non-consensual sharing of private information (doxxing).</li>
          <li>
            Use block and report tools; escalate via{" "}
            <Link href="/report">Report</Link> when needed.
          </li>
        </ul>
      </LegalSection>

      <LegalSection id="scams" title="Scams & fraud">
        <ul>
          <li>No fake tickets, payment redirection off-platform for “deals.”</li>
          <li>No phishing for OTPs, passwords, or QR codes.</li>
          <li>No chargeback abuse or inventory manipulation.</li>
        </ul>
        <p>
          Prefer checkout on {brand.name} so disputes have an order trail. See{" "}
          <Link href="/safety">Safety</Link>.
        </p>
      </LegalSection>

      <LegalSection id="impersonation" title="Impersonation">
        <p>
          Do not impersonate other people, hosts, brands, venues, or {brand.name}{" "}
          staff. Misleading profiles, listings, or ambassador pages may be
          removed and accounts restricted.
        </p>
      </LegalSection>

      <LegalSection id="unsafe-events" title="Unsafe events">
        <p>
          Do not list or promote events that knowingly endanger attendees, evade
          required permits, or hide critical safety risks. Hosts must take
          reasonable care for venue readiness and on-site operations. Report
          suspicious listings via <Link href="/report">Report</Link>.
        </p>
      </LegalSection>

      <LegalSection id="prohibited-content" title="Prohibited content">
        <p>
          Illegal content, exploitative material, malware, spam, and IP-infringing
          uploads are not allowed on Passports, Vault teasers, listings,
          messages, or reviews.
        </p>
      </LegalSection>

      <LegalSection id="fan-connect" title="Fan Connect behavior">
        <p>
          Fan Connect is for genuine, optional connection — not spam, pressure,
          or harassment. Honor privacy settings, consent, and remove/block
          outcomes. Nearby discovery stays opt-in.
        </p>
      </LegalSection>

      <LegalSection id="messaging" title="Messaging rules">
        <ul>
          <li>Keep conversations relevant and respectful.</li>
          <li>Do not share payment secrets, OTPs, or QR secrets in chat.</li>
          <li>
            Fan↔fan messaging generally requires mutual Connect where that
            product path applies.
          </li>
        </ul>
      </LegalSection>

      <LegalSection id="reviews" title="Review rules">
        <p>
          Reviews should reflect real attendance or genuine experience. Do not
          post fake reviews, bribed ratings, or abusive review content. Hosts
          cannot delete reviews to hide feedback; moderation follows platform
          rules.
        </p>
      </LegalSection>

      <LegalSection id="ambassadors" title="Ambassador conduct">
        <p>
          Promote honestly. No fake traffic, misleading claims, or harvesting
          buyer data you are not entitled to see. Fraudulent conversions can be
          reversed and campaigns or accounts restricted.
        </p>
      </LegalSection>

      <LegalSection id="hosts" title="Host conduct">
        <p>
          Describe events accurately, honor published access rules, and
          communicate changes promptly. Do not misuse attendee data from door or
          CRM tools. Misleading promotions undermine trust for everyone.
        </p>
      </LegalSection>

      <LegalSection id="enforcement" title="Enforcement">
        <p>
          {brand.name} may remove content, void abusive tickets, limit features,
          pause listings, or suspend accounts. Eligible users can appeal via{" "}
          <Link href="/account/appeal">Account appeal</Link>. For immediate
          danger, contact local emergency services first, then{" "}
          <Link href="/report">report on {brand.name}</Link>.
        </p>
      </LegalSection>
    </>
  );
}
