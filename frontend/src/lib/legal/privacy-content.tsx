import Link from "next/link";

import { LegalSection } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import {
  PLATFORM_RELATIONSHIP_TOC,
  PlatformRelationshipSection,
} from "@/lib/legal/platform-relationship";
import { legalToc } from "@/lib/legal/toc";

export const PRIVACY_TOC = legalToc(
  { id: "overview", title: "Overview" },
  PLATFORM_RELATIONSHIP_TOC,
  { id: "account-data", title: "Account data" },
  { id: "guest-checkout", title: "Guest checkout data" },
  { id: "orders-tickets", title: "Ticket & order data" },
  { id: "attendees", title: "Attendee & recipient data" },
  { id: "host-data", title: "Host data" },
  { id: "fan-passport", title: "Fan Passport visibility" },
  { id: "fan-connect", title: "Fan Connect visibility" },
  { id: "messages-reports", title: "Messages & reports" },
  { id: "location", title: "Location & geolocation" },
  { id: "payments", title: "Payment processing" },
  { id: "notifications", title: "Notifications" },
  { id: "support", title: "Support tickets" },
  { id: "admin-logs", title: "Admin & moderation records" },
  { id: "cookies", title: "Cookies & analytics" },
  { id: "sharing", title: "Sharing with hosts & processors" },
  { id: "controls", title: "Your controls" },
  { id: "retention", title: "Retention" },
  { id: "security", title: "Security" },
  { id: "contact", title: "Contact" },
);

export function PrivacyContent() {
  return (
    <>
      <LegalSection id="overview" title="Overview">
        <p>
          This Privacy Policy explains how {brand.name} collects, uses, shares,
          and protects personal information when you use our marketplace for
          events, ticketing, hosting, fan identity, and related services. We do
          not sell your personal data as a standalone product.
        </p>
        <p>
          Related documents: <Link href="/cookies">Cookie Policy</Link>,{" "}
          <Link href="/terms">Terms</Link>, and <Link href="/safety">Safety</Link>.
        </p>
      </LegalSection>

      <PlatformRelationshipSection />

      <LegalSection id="account-data" title="Account data">
        <p>When you register or update an account, we may process:</p>
        <ul>
          <li>Name, email, phone (when provided), and login credentials</li>
          <li>Profile preferences, notification settings, and role context (fan/host)</li>
          <li>Security signals such as session and device information</li>
        </ul>
      </LegalSection>

      <LegalSection id="guest-checkout" title="Guest checkout data">
        <p>
          Guest buyers provide contact and purchase details needed to complete
          checkout, deliver tickets, prevent fraud, and support refunds — even
          without creating an account first. Claiming tickets later may link that
          order history to an account you control.
        </p>
      </LegalSection>

      <LegalSection id="orders-tickets" title="Ticket & order data">
        <p>
          We process order references, ticket types, amounts, statuses,
          check-in state, and related fulfilment records so tickets can be
          issued, scanned, transferred (where enabled), and supported. Tickets
          are issued only after verified payment or confirmed free reservation.
        </p>
      </LegalSection>

      <LegalSection id="attendees" title="Attendee & recipient data">
        <p>
          If you buy for someone else or enter attendee fields, we process the
          names and details you supply so hosts can manage entry and so we can
          deliver access. Provide only information you are authorized to share.
        </p>
      </LegalSection>

      <LegalSection id="host-data" title="Host data">
        <p>
          Hosts provide business/profile details, event content, team member
          invites, payout-related information, and operational records needed to
          run Event Studio, check-in, merch, Ambassadors, sponsorships, and
          finance tools. Team tools are designed to limit exposure of buyer
          secrets at the door.
        </p>
      </LegalSection>

      <LegalSection id="fan-passport" title="Fan Passport visibility">
        <p>
          Fan Passport defaults toward private controls. Public or directory
          visibility is based on settings you choose. Public serializers are
          designed not to expose email, phone, payment amounts, hidden venues,
          or locked Vault media.
        </p>
      </LegalSection>

      <LegalSection id="fan-connect" title="Fan Connect visibility">
        <p>
          Fan Connect is optional. Discovery and connection requests depend on
          your Connect settings. Shared context uses public-safe signals (such as
          shared upcoming events you both surface) — not private ticket
          internals, payment data, or locked content. Removing or blocking a
          connection limits further messaging according to product rules.
        </p>
      </LegalSection>

      <LegalSection id="messages-reports" title="Messages & reports">
        <p>
          Message content is processed to deliver conversations between
          permitted participants. Notifications use limited preview copy.
          Reports you submit (abuse, fraud, safety) are reviewed by authorized
          staff. Do not include passwords, OTPs, full card numbers, or QR
          secrets in reports.
        </p>
      </LegalSection>

      <LegalSection id="location" title="Location & geolocation">
        <p>
          Event location fields may be partially hidden until purchase or a host
          reveal rule. Optional features such as nearby discovery or “near me”
          may use approximate location only with your consent or device
          permission. You can decline device location; some discovery features
          will be limited.
        </p>
      </LegalSection>

      <LegalSection id="payments" title="Payment processing">
        <p>
          Card and checkout data are handled by payment partners.
          {brand.name} stores payment references and statuses needed
          for orders, refunds, payouts, and fraud prevention — not full card
          PANs for you to paste into chats. Never send payment secrets through
          messaging.
        </p>
      </LegalSection>

      <LegalSection id="notifications" title="Notifications">
        <p>
          We send transactional notices (tickets, claims, security, support) and,
          where you opt in, product updates. Control preferences in account
          settings where available.
        </p>
      </LegalSection>

      <LegalSection id="support" title="Support tickets">
        <p>
          Support conversations include the details you submit so we can help
          with orders, accounts, and reports. Keep sensitive secrets out of
          ticket bodies; share order references instead.
        </p>
      </LegalSection>

      <LegalSection id="admin-logs" title="Admin & moderation records">
        <p>
          Authorized staff may access operational records to review reports,
          prevent fraud, handle refunds, and keep the Platform safe. Internal
          staff notes are not shown to other users. We do not publish private
          message bodies, QR secrets, or payment secrets on public pages.
        </p>
      </LegalSection>

      <LegalSection id="cookies" title="Cookies & analytics">
        <p>
          We use cookies and similar browser storage (including localStorage and
          sessionStorage) for sign-in state, security, preferences, ambassador
          referral attribution, and privacy-conscious analytics where enabled.
          Sign-in is stored in localStorage and sent via API Authorization
          headers—not traditional login cookies. Details are in the{" "}
          <Link href="/cookies">Cookie Policy</Link>.
        </p>
      </LegalSection>

      <LegalSection id="sharing" title="Sharing with hosts & processors">
        <p>We share personal data only as needed to operate the Platform, including:</p>
        <ul>
          <li>
            <strong>Hosts / door teams:</strong> purchase and attendee details
            required to run entry, fulfilment, and legitimate event operations —
            not unrestricted dumps of payment secrets or QR secrets.
          </li>
          <li>
            <strong>Processors:</strong> payment, hosting, email/SMS delivery,
            analytics, and similar vendors under contracts that limit use.
          </li>
          <li>
            <strong>Legal / safety:</strong> when required by law or necessary to
            protect users, rights, or the Platform.
          </li>
        </ul>
      </LegalSection>

      <LegalSection id="controls" title="Your controls">
        <ul>
          <li>Update profile, Passport, and Connect privacy settings.</li>
          <li>Manage notification preferences where offered.</li>
          <li>
            Request access or deletion via <Link href="/support">Support</Link>{" "}
            where applicable under local law and operational limits (for example,
            records we must keep for fraud, taxes, or disputes).
          </li>
        </ul>
      </LegalSection>

      <LegalSection id="retention" title="Retention">
        <p>
          We retain personal data as needed to provide services, resolve
          disputes, meet legal and financial obligations, and maintain security.
          Retention periods vary by record type (accounts, orders, support,
          audit).
        </p>
      </LegalSection>

      <LegalSection id="security" title="Security">
        <p>
          We apply access controls, monitoring, and operational practices
          designed to protect personal data. No method of transmission or
          storage is perfectly secure. Report suspected account compromise
          through Support promptly.
        </p>
      </LegalSection>

      <LegalSection id="contact" title="Contact">
        <p>
          Privacy questions: <Link href="/support">Support</Link> or{" "}
          <Link href="/contact">Contact</Link>. For safety emergencies, contact
          local authorities first, then report on-platform via{" "}
          <Link href="/report">Report</Link>.
        </p>
      </LegalSection>
    </>
  );
}
