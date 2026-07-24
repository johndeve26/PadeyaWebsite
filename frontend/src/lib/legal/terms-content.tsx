import Link from "next/link";

import { LegalSection } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import {
  PLATFORM_RELATIONSHIP_TOC,
  PlatformRelationshipSection,
} from "@/lib/legal/platform-relationship";
import { legalToc } from "@/lib/legal/toc";

export const TERMS_TOC = legalToc(
  { id: "acceptance", title: "Acceptance of terms" },
  PLATFORM_RELATIONSHIP_TOC,
  { id: "accounts", title: "User accounts" },
  { id: "guest-checkout", title: "Guest checkout" },
  { id: "tickets", title: "Ticket purchases" },
  { id: "buying-for-others", title: "Buying for someone else" },
  { id: "ticket-delivery", title: "Ticket delivery" },
  { id: "qr-rules", title: "QR ticket rules" },
  { id: "host-responsibilities", title: "Host responsibilities" },
  { id: "buyer-responsibilities", title: "Buyer & fan responsibilities" },
  { id: "event-changes", title: "Event changes & cancellations" },
  { id: "payments-fees", title: "Payments & fees" },
  { id: "refunds", title: "Refunds" },
  { id: "merch-vault", title: "Merch & Vault" },
  { id: "fan-passport", title: "Fan Passport" },
  { id: "fan-connect", title: "Fan Connect & messaging" },
  { id: "ambassadors", title: "Ambassadors & referrals" },
  { id: "sponsorships", title: "Sponsorship marketplace" },
  { id: "prohibited", title: "Prohibited conduct" },
  { id: "restrictions", title: "Restrictions, suspensions & appeals" },
  { id: "ip", title: "Intellectual property" },
  { id: "ugc", title: "User-generated content" },
  { id: "liability", title: "Limitation of liability" },
  { id: "termination", title: "Account termination" },
  { id: "support", title: "Support & contact" },
  { id: "updates", title: "Updates to these Terms" },
);

export function TermsContent() {
  return (
    <>
      <LegalSection id="acceptance" title="Acceptance of terms">
        <p>
          These Terms of Service (“Terms”) govern access to and use of {brand.name}{" "}
          websites, apps, and related services (the “Platform”). By browsing,
          creating an account, completing guest checkout, buying tickets or merch,
          unlocking Vault items, hosting events, promoting as an ambassador,
          exploring sponsorships, or otherwise using the Platform, you agree to
          these Terms and to our{" "}
          <Link href="/privacy">Privacy Policy</Link>,{" "}
          <Link href="/cookies">Cookie Policy</Link>,{" "}
          <Link href="/ticket-policy">Ticket Policy</Link>,{" "}
          <Link href="/refund-policy">Refund Policy</Link>, and{" "}
          <Link href="/community-guidelines">Community Guidelines</Link>.
        </p>
        <p>
          If you do not agree, do not use the Platform. If you use {brand.name} on
          behalf of an organization, you represent that you have authority to
          bind that organization.
        </p>
      </LegalSection>

      <PlatformRelationshipSection showRelatedLinks={false} />

      <LegalSection id="accounts" title="User accounts">
        <ul>
          <li>
            Provide accurate registration details and keep your credentials
            secure. You are responsible for activity under your account.
          </li>
          <li>
            Notify Support promptly if you suspect unauthorized access.
          </li>
          <li>
            Some features (hosting, Fan Passport tools, Fan Connect, Ambassadors,
            payouts) require a verified or eligible account.
          </li>
          <li>
            {brand.name} may refuse registration, require additional verification,
            or limit features where risk, abuse, or legal concerns arise.
          </li>
        </ul>
      </LegalSection>

      <LegalSection id="guest-checkout" title="Guest checkout">
        <p>
          Where a host enables guest checkout, you may purchase tickets without
          signing in first by providing required buyer details and completing
          payment. Guest purchases still create order and ticket records needed
          for delivery, entry, support, and refunds.
        </p>
        <p>
          Guest buyers can claim tickets into an account after purchase where
          that flow is offered. Merch-only or certain bundle flows may still
          require an account.
        </p>
      </LegalSection>

      <LegalSection id="tickets" title="Ticket purchases">
        <p>
          Event details — including time, venue visibility, ticket tiers, age
          rules, and inclusions — are set by hosts. You agree to review listing
          details before paying. Tickets are issued only after payment is
          verified through our payment partners (or after free RSVP confirmation
          where offered), not solely because a browser shows a success page.
        </p>
        <p>
          Ticket rules are described further in the{" "}
          <Link href="/ticket-policy">Ticket Policy</Link>.
        </p>
      </LegalSection>

      <LegalSection id="buying-for-others" title="Buying for someone else">
        <p>
          You may buy tickets for other attendees when the product allows
          recipient or attendee details. You are responsible for providing
          accurate attendee information and ensuring recipients receive access
          instructions. Hosts may still require the named attendee or valid ID
          at the door for restricted tiers.
        </p>
      </LegalSection>

      <LegalSection id="ticket-delivery" title="Ticket delivery">
        <p>
          After verified payment or confirmed free reservation, tickets appear
          in the buyer’s account (or claim flow for guests) and may also be
          confirmed by email. Keep order references for support. Delivery timing
          can depend on payment confirmation and network conditions.
        </p>
      </LegalSection>

      <LegalSection id="qr-rules" title="QR ticket rules">
        <ul>
          <li>
            Valid entry typically requires a ticket issued by {brand.name} with a
            signed QR presented for host or venue scanning.
          </li>
          <li>
            Do not share QR codes to enable multi-entry fraud. Checked-in or
            voided tickets may be rejected.
          </li>
          <li>
            Prefer the live ticket in-app over unverified screenshots when
            possible. Hosts control door decisions subject to venue rules.
          </li>
        </ul>
      </LegalSection>

      <LegalSection id="host-responsibilities" title="Host responsibilities">
        <p>If you host on {brand.name}, you agree that you are responsible for:</p>
        <ul>
          <li>Accurate listings (schedule, access, what’s included, pricing).</li>
          <li>
            Permits, venue readiness, safety planning, crowd control, age
            restrictions, accessibility arrangements, and on-site operations.
          </li>
          <li>
            Communicating changes, cancellations, entry rules, and applicable
            refund terms to buyers.
          </li>
          <li>
            Lawful use of attendee data you receive for fulfilment, and honoring
            platform privacy rules at the door and in team tools.
          </li>
          <li>
            Paying applicable platform and payment-partner fees on successful
            sales.
          </li>
        </ul>
      </LegalSection>

      <LegalSection id="buyer-responsibilities" title="Buyer & fan responsibilities">
        <ul>
          <li>Review event details, fees, and host policies before purchase.</li>
          <li>
            Arrive with a valid ticket and any ID or dress-code requirements
            stated by the host or venue.
          </li>
          <li>
            Do not attempt to bypass check-in, resell against host rules, or use
            the Platform for fraud or harassment.
          </li>
          <li>
            Prefer on-platform checkout so orders have a clear audit trail for
            support.
          </li>
        </ul>
      </LegalSection>

      <LegalSection id="event-changes" title="Event changes & cancellations">
        <p>
          Hosts may change or cancel events. {brand.name} may also take
          moderation actions on listings for safety, fraud, abuse, legal, or
          platform-risk reasons. Refund eligibility for cancellations and
          reschedules follows the{" "}
          <Link href="/refund-policy">Refund Policy</Link> and any host terms
          shown at purchase.
        </p>
      </LegalSection>

      <LegalSection id="payments-fees" title="Payments & fees">
        <p>
          Paid checkout is processed by payment partners.
          Platform fees may apply to hosts on successful sales. Buyer-facing
          totals are shown at checkout before you pay. Fee context for hosts is
          described on <Link href="/pricing">Pricing</Link> and in host finance
          views. Do not share OTPs, full card numbers, or payment secrets in
          messages or support tickets.
        </p>
      </LegalSection>

      <LegalSection id="refunds" title="Refunds">
        <p>
          Refunds are governed by the{" "}
          <Link href="/refund-policy">Refund Policy</Link>. Not every purchase is
          automatically refundable. Approved refunds generally return through
          the original payment path when possible; bank timelines vary.
        </p>
      </LegalSection>

      <LegalSection id="merch-vault" title="Merch & Vault">
        <p>
          Hosts may offer merchandise and Vault content. Merch fulfilment
          (shipping or pickup) is primarily a host responsibility once payment
          is verified. Vault unlocks grant access according to host-set rules
          after verification. Refunds for merch or Vault follow the Refund
          Policy and product-specific rules shown at purchase.
        </p>
      </LegalSection>

      <LegalSection id="fan-passport" title="Fan Passport">
        <p>
          Fan Passport lets you build a fan identity with visibility controls you
          choose. Public profiles should not expose payment secrets, private
          messages, or hidden venue details. You are responsible for content you
          publish on your Passport.
        </p>
      </LegalSection>

      <LegalSection id="fan-connect" title="Fan Connect & messaging">
        <p>
          Fan Connect is optional and privacy-controlled. Messaging is generally
          fan↔host for event coordination, and fan↔fan only after mutual Connect
          acceptance where enabled. Do not use messaging for spam, scams,
          harassment, or sharing illegal content. Block and report tools are
          available; see <Link href="/safety">Safety</Link>.
        </p>
      </LegalSection>

      <LegalSection id="ambassadors" title="Ambassadors & referrals">
        <p>
          Ambassador or promo codes may reward tracked promotions after verified
          paid conversions, subject to campaign rules. Fraudulent self-referral,
          fake traffic, or abuse can reverse rewards and lead to account action.
          Ambassadors do not receive buyer contact data or door credentials by
          promoting alone.
        </p>
      </LegalSection>

      <LegalSection id="sponsorships" title="Sponsorship marketplace">
        <p>
          Sponsorship packages and inquiries are tools for hosts and brands to
          connect. Unless {brand.name} expressly states otherwise for a specific
          program, commercial terms of a sponsorship are between host and brand.
          {brand.name} provides marketplace workflow and may moderate listings
          that violate policy.
        </p>
      </LegalSection>

      <LegalSection id="prohibited" title="Prohibited conduct">
        <p>You must not:</p>
        <ul>
          <li>Commit fraud, money laundering, or payment abuse.</li>
          <li>Harass, threaten, dox, or discriminate against others.</li>
          <li>Impersonate people, brands, or {brand.name} staff.</li>
          <li>List unsafe or illegally operated events, or misrepresent access.</li>
          <li>
            Scrape, reverse engineer, or bypass access controls, including ticket
            QR misuse.
          </li>
          <li>Upload malware or content that infringes others’ rights.</li>
          <li>Use the Platform to facilitate illegal activity.</li>
        </ul>
      </LegalSection>

      <LegalSection id="restrictions" title="Restrictions, suspensions & appeals">
        <p>
          {brand.name} may restrict features, remove content, void abusive
          tickets, pause listings, or suspend accounts to protect users and the
          Platform. Where available, you may submit an appeal via{" "}
          <Link href="/account/appeal">Account appeal</Link>. Appeals are
          reviewed separately from ordinary support tickets.
        </p>
      </LegalSection>

      <LegalSection id="ip" title="Intellectual property">
        <p>
          {brand.name} branding, software, and platform materials are owned by{" "}
          {brand.name} or its licensors. You may not copy, frame, or exploit them
          except as allowed by these Terms or written permission. Hosts and fans
          retain rights to their own original content, subject to the license
          below.
        </p>
      </LegalSection>

      <LegalSection id="ugc" title="User-generated content">
        <p>
          You grant {brand.name} a worldwide, non-exclusive license to host,
          display, reproduce, and distribute content you upload as needed to
          operate and promote the Platform (including event discovery surfaces).
          You represent you have rights to the content you submit. We may remove
          content that violates policy or law.
        </p>
      </LegalSection>

      <LegalSection id="liability" title="Limitation of liability">
        <p>
          The Platform is provided on an “as available” basis. To the fullest
          extent permitted by law, {brand.name} is not liable for host-run event
          quality, venue conditions, performer cancellations, personal injury at
          third-party events, off-platform payments, or losses caused by factors
          outside reasonable platform control.
        </p>
        <p>
          Nothing in these Terms excludes liability that cannot be limited under
          applicable law. {brand.name} does not guarantee uninterrupted service,
          perfect security, or that every listing is accurate.
        </p>
      </LegalSection>

      <LegalSection id="termination" title="Account termination">
        <p>
          You may stop using the Platform at any time. {brand.name} may suspend
          or terminate access for policy violations, legal requirements, or
          prolonged inactivity where permitted. Provisions that by nature should
          survive (including IP, liability limits, and accrued payment
          obligations) continue after termination.
        </p>
      </LegalSection>

      <LegalSection id="support" title="Support & contact">
        <p>
          For help with orders, accounts, or reports, use{" "}
          <Link href="/support">Support</Link>,{" "}
          <Link href="/report">Report</Link>, or{" "}
          <Link href="/contact">Contact</Link>. For immediate danger, contact
          local emergency services first.
        </p>
      </LegalSection>

      <LegalSection id="updates" title="Updates to these Terms">
        <p>
          We may update these Terms to reflect product, legal, or operational
          changes. The “Last updated” date on this page will change when we do.
          Continued use after an update means you accept the revised Terms. If
          you do not agree, stop using the Platform.
        </p>
      </LegalSection>
    </>
  );
}
