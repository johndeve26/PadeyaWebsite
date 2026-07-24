import Link from "next/link";

import { LegalSection } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import {
  PLATFORM_RELATIONSHIP_TOC,
  PlatformRelationshipSection,
} from "@/lib/legal/platform-relationship";
import { legalToc } from "@/lib/legal/toc";

export const TICKET_TOC = legalToc(
  { id: "ownership", title: "Ticket ownership & access" },
  PLATFORM_RELATIONSHIP_TOC,
  { id: "issuance", title: "QR issuance after payment" },
  { id: "guest", title: "Guest checkout tickets" },
  { id: "someone-else", title: "Tickets bought for someone else" },
  { id: "group", title: "Group tickets" },
  { id: "transfers", title: "Transfers" },
  { id: "check-in", title: "Check-in rules" },
  { id: "reuse", title: "Duplicate QR & reuse" },
  { id: "lost", title: "Lost ticket access" },
  { id: "entry-control", title: "Host & venue entry control" },
  { id: "venue-rules", title: "Age, ID, dress code & venue rules" },
  { id: "location-reveal", title: "Location revealed after payment" },
  { id: "invalid", title: "Invalid or cancelled tickets" },
);

export function TicketPolicyContent() {
  return (
    <>
      <LegalSection id="ownership" title="Ticket ownership & access">
        <p>
          A {brand.name} ticket grants the holder access rights described by the
          ticket type and host listing, subject to this Ticket Policy, the{" "}
          <Link href="/terms">Terms</Link>, and host/venue rules. Ownership is
          reflected in platform records after verified issuance. Screenshots are
          not a guarantee of validity if the underlying ticket is voided,
          transferred, or already checked in.
        </p>
      </LegalSection>

      <PlatformRelationshipSection />

      <LegalSection id="issuance" title="QR issuance after payment">
        <p>
          Signed QR tickets are issued only after payment is verified through
          our payment partners, or after free RSVP confirmation where offered.
          Browser “success” pages alone do not create entry rights. Inventory
          commits follow verified settlement.
        </p>
      </LegalSection>

      <LegalSection id="guest" title="Guest checkout tickets">
        <p>
          Guest checkout tickets are delivered using the buyer details provided
          at purchase (commonly email confirmation) and can be claimed into an
          account afterward. Keep your order reference to reclaim access if you
          change devices.
        </p>
      </LegalSection>

      <LegalSection id="someone-else" title="Tickets bought for someone else">
        <p>
          When you enter attendee or recipient details, those individuals may be
          the expected entrants. Hosts may require matching ID for age-restricted
          or named tiers. You remain responsible for accurate details and for
          sharing access instructions with recipients.
        </p>
      </LegalSection>

      <LegalSection id="group" title="Group tickets">
        <p>
          Group or multi-quantity purchases may issue multiple ticket passes
          under one order. Each pass is typically scanned separately at the
          door. Follow host instructions for group entry and any table/VIP
          packages.
        </p>
      </LegalSection>

      <LegalSection id="transfers" title="Transfers">
        <p>
          Where transfers are enabled for a ticket, you may transfer to another{" "}
          {brand.name} user before check-in according to in-product rules. After
          acceptance or scan, ownership follows platform status. Hosts may
          disable transfers for certain events or tiers.
        </p>
      </LegalSection>

      <LegalSection id="check-in" title="Check-in rules">
        <ul>
          <li>Present your QR for scanning by host staff or venue partners.</li>
          <li>Live in-app tickets are preferred over unverified copies.</li>
          <li>
            Offline or delayed connectivity can affect scan UX; staff may use
            host tools to resolve legitimate tickets.
          </li>
        </ul>
      </LegalSection>

      <LegalSection id="reuse" title="Duplicate QR & reuse">
        <p>
          A checked-in QR is not meant for multiple entries. Sharing codes to
          enable fraud, or attempting reuse after scan, can void tickets and
          lead to account action under the{" "}
          <Link href="/community-guidelines">Community Guidelines</Link>.
        </p>
      </LegalSection>

      <LegalSection id="lost" title="Lost ticket access">
        <p>
          If you lose device access, sign in (or claim the guest order) and open{" "}
          <Link href="/dashboard/tickets">My tickets</Link>. Support can help
          verify ownership using order references — not by asking you for QR
          secrets in chat. Hosts/support may revoke or regenerate credentials
          only through official ticket tools when misuse is suspected.
        </p>
      </LegalSection>

      <LegalSection id="entry-control" title="Host & venue entry control">
        <p>
          Final entry decisions at the door are controlled by the host and
          venue, including capacity, security screening, and local rules.{" "}
          {brand.name} provides ticketing and scan tooling; it does not replace
          on-site security or venue management.
        </p>
      </LegalSection>

      <LegalSection id="venue-rules" title="Age, ID, dress code & venue rules">
        <p>
          Obey age restrictions, ID checks, dress codes, and venue policies
          stated by the host or venue. Failure to meet those requirements can
          result in denied entry without a platform refund when the listing
          disclosed the rules.
        </p>
      </LegalSection>

      <LegalSection id="location-reveal" title="Location revealed after payment">
        <p>
          Some events hide precise addresses until purchase or another host
          reveal rule. Exact streets and private join details are not meant for
          public scraping. After purchase, check your ticket and confirmation
          for reveal timing and any host notes.
        </p>
      </LegalSection>

      <LegalSection id="invalid" title="Invalid or cancelled tickets">
        <p>
          Tickets may be invalid if payment reverses, fraud is detected, a
          transfer completes to someone else, the ticket is cancelled/voided, or
          the event is cancelled. Refund paths for cancellations are described
          in the <Link href="/refund-policy">Refund Policy</Link>.
        </p>
      </LegalSection>
    </>
  );
}
