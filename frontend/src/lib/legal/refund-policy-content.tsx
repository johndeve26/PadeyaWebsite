import Link from "next/link";

import { LegalSection } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import {
  PLATFORM_RELATIONSHIP_TOC,
  PlatformRelationshipSection,
} from "@/lib/legal/platform-relationship";
import { legalToc } from "@/lib/legal/toc";

export const REFUND_TOC = legalToc(
  { id: "how-refunds-work", title: "How refunds work" },
  PLATFORM_RELATIONSHIP_TOC,
  { id: "host-rules", title: "Host refund rules" },
  { id: "platform-role", title: "Platform & support role" },
  { id: "cancelled", title: "Cancelled events" },
  { id: "rescheduled", title: "Rescheduled events" },
  { id: "duplicate-failed", title: "Duplicate or failed payments" },
  { id: "guest", title: "Guest checkout refunds" },
  { id: "merch", title: "Merch refunds" },
  { id: "vault", title: "Vault refunds" },
  { id: "fees", title: "Fees & non-refundable amounts" },
  { id: "abuse", title: "Abuse & fraud" },
  { id: "timelines", title: "Refund timelines" },
  { id: "request", title: "How to request a refund" },
);

export function RefundPolicyContent() {
  return (
    <>
      <LegalSection id="how-refunds-work" title="How refunds work">
        <p>
          Refund eligibility on {brand.name} depends on event status, host
          policy, product type (tickets, merch, Vault), payment settlement, and
          platform review where needed. Not every purchase is automatically
          refundable. Checkout and listing copy may describe host-specific
          terms; this policy explains how refunds generally work across the
          marketplace.
        </p>
      </LegalSection>

      <PlatformRelationshipSection />

      <LegalSection id="host-rules" title="Host refund rules">
        <p>
          Hosts may configure refund-related policies for their events within
          platform rules. Hosts remain responsible for communicating those terms
          and for operational decisions about cancellations and changes. Buyer
          outcomes still follow this Refund Policy, the{" "}
          <Link href="/ticket-policy">Ticket Policy</Link>, and what was shown
          at purchase.
        </p>
      </LegalSection>

      <LegalSection id="platform-role" title="Platform & support role">
        <p>
          {brand.name} provides refund request workflows, payment-partner
          refunds when approved, and support/finance review for eligible cases.
          Support helps investigate orders; it does not invent payment outcomes
          outside verified records. Support cannot mark host payouts as paid.
        </p>
      </LegalSection>

      <LegalSection id="cancelled" title="Cancelled events">
        <p>
          When an event is cancelled by the host or removed/paused by the
          platform for safety or policy reasons, eligible ticket purchases are
          typically considered for refund according to settlement status and
          product rules. Keep your order reference when contacting Support.
        </p>
      </LegalSection>

      <LegalSection id="rescheduled" title="Rescheduled events">
        <p>
          If a host reschedules, tickets often remain valid for the new date
          unless the host or platform states otherwise. Refund options for
          reschedules depend on host policy and what was communicated to buyers.
          Review host messages and your ticket dashboard after a schedule
          change.
        </p>
      </LegalSection>

      <LegalSection id="duplicate-failed" title="Duplicate or failed payments">
        <p>
          Duplicate or failed charges after payment verification may be eligible
          for correction once we confirm settlement status with our payment
          partner. Provide the order or payment reference and bank statement
          snippet (without full card numbers) if Support requests evidence.
        </p>
      </LegalSection>

      <LegalSection id="guest" title="Guest checkout refunds">
        <p>
          Guest buyers can request refunds using the email and order reference
          from purchase, via Support ticket flows or by claiming the order into
          an account and using{" "}
          <Link href="/dashboard/refunds">Personal → Refunds</Link> where
          available. Access to the original confirmation details helps us verify
          ownership.
        </p>
      </LegalSection>

      <LegalSection id="merch" title="Merch refunds">
        <p>
          Merch refunds depend on fulfilment status (unshipped, shipped, picked
          up), host policy, and whether items were personalized or digital.
          Report damaged or incorrect items promptly with order details. Hosts
          handle many fulfilment outcomes; platform Support can help mediate
          using order records. For how merch sells on {brand.name}, see{" "}
          <Link href="/merch-guide">Merch guide</Link>.
        </p>
      </LegalSection>

      <LegalSection id="vault" title="Vault refunds">
        <p>
          Paid Vault unlocks are often non-refundable after access is granted,
          except where required by law, where payment failed/duplicated, or
          where {brand.name} approves a case (for example, undeliverable access
          due to a verified platform fault). Free unlocks have no monetary
          refund.
        </p>
      </LegalSection>

      <LegalSection id="fees" title="Fees & non-refundable amounts">
        <p>
          Where payment-partner or platform fees are non-recoverable on a
          partial reversal, approved refunds may reflect net recoverable
          amounts. Checkout shows buyer totals before you pay. See{" "}
          <Link href="/pricing">Pricing</Link> for host fee context.
        </p>
      </LegalSection>

      <LegalSection id="abuse" title="Abuse & fraud">
        <p>
          Refunds may be denied or reversed, and accounts restricted, where we
          detect fraud, chargeback abuse, ticket misuse, fake attendance claims,
          or policy evasion. {brand.name} may share necessary records with
          payment partners to investigate.
        </p>
      </LegalSection>

      <LegalSection id="timelines" title="Refund timelines">
        <p>
          After approval, refunds return through the original payment path when
          possible. Bank and card networks set their own posting timelines —
          often several business days. {brand.name} cannot control issuer
          posting speed.
        </p>
      </LegalSection>

      <LegalSection id="request" title="How to request a refund">
        <ol>
          <li>
            Signed-in buyers: start at{" "}
            <Link href="/dashboard/refunds">Personal → Refunds</Link>.
          </li>
          <li>
            Guests or complex cases: open{" "}
            <Link href="/support/new?category=payments_refunds">Support</Link>{" "}
            with your order reference.
          </li>
          <li>
            Include event name, purchase email, and a clear reason. Do not send
            OTPs, full card numbers, or QR secrets.
          </li>
        </ol>
        <p>
          Typical refund-friendly cases include host/platform cancellations and
          verified duplicate charges. Change of mind after an entry-ready ticket
          issues, buyer travel mistakes, and transferred tickets already
          accepted by another user are commonly not refundable.
        </p>
      </LegalSection>
    </>
  );
}
