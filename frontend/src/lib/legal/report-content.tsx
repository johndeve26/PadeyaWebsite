import Link from "next/link";

import { LegalSection } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import { legalToc } from "@/lib/legal/toc";

export const REPORT_TOC = legalToc(
  { id: "how-to-report", title: "How to report" },
  { id: "event", title: "Report an event" },
  { id: "host", title: "Report a host" },
  { id: "user", title: "Report a user" },
  { id: "message", title: "Report a message" },
  { id: "payment", title: "Report a payment or order issue" },
  { id: "safety", title: "Report a safety concern" },
  { id: "fraud", title: "Report impersonation or fraud" },
  { id: "what-to-include", title: "What to include" },
  { id: "emergencies", title: "Emergencies" },
);

const paths = [
  {
    id: "event",
    title: "Report an event",
    body: "Misleading listings, unsafe venue claims, or events that violate community rules.",
    href: "/support/new?category=event_issue",
  },
  {
    id: "host",
    title: "Report a host",
    body: "Host conduct, door problems, or repeated policy concerns tied to a host profile.",
    href: "/support/new?category=event_issue",
  },
  {
    id: "user",
    title: "Report a user",
    body: "Passport abuse, harassment, or impersonation on fan profiles.",
    href: "/support/new?category=messaging_abuse",
  },
  {
    id: "message",
    title: "Report a message",
    body: "Abusive chats, spam, or scam attempts in messaging or Fan Connect.",
    href: "/support/new?category=messaging_abuse",
  },
  {
    id: "payment",
    title: "Report a payment or order issue",
    body: "Suspicious charges, missing tickets after verified payment, or refund problems.",
    href: "/support/new?category=payments_refunds",
  },
  {
    id: "safety",
    title: "Report a safety concern",
    body: "Threats, stalking, or other safety risks connected to platform activity.",
    href: "/support/new?category=messaging_abuse",
  },
  {
    id: "fraud",
    title: "Report impersonation or fraud",
    body: "Fake tickets, phishing for OTPs, or someone pretending to be staff or a brand.",
    href: "/support/new?category=payments_refunds",
  },
] as const;

export function ReportContent() {
  return (
    <>
      <LegalSection id="how-to-report" title="How to report">
        <p>
          Use a tracked Support ticket so {brand.name} can route your report.
          Choose the closest category below. In-product report buttons (where
          shown) also create reviewable cases.
        </p>
        <p>
          Related: <Link href="/safety">Safety Center</Link>,{" "}
          <Link href="/community-guidelines">Community Guidelines</Link>,{" "}
          <Link href="/support">Support</Link>.
        </p>
      </LegalSection>

      {paths.map((p) => (
        <LegalSection key={p.id} id={p.id} title={p.title}>
          <p>{p.body}</p>
          <p>
            <Link href={p.href}>Open a Support ticket →</Link>
          </p>
        </LegalSection>
      ))}

      <LegalSection id="what-to-include" title="What to include">
        <ul>
          <li>Links, usernames, event names, or order references</li>
          <li>Dates/times and a clear description of what happened</li>
          <li>Screenshots that do not show passwords, OTPs, full cards, or QR secrets</li>
        </ul>
        <p>
          Do not paste payment secrets, private message dumps you are not allowed
          to share, or ticket QR payloads into reports.
        </p>
      </LegalSection>

      <LegalSection id="emergencies" title="Emergencies">
        <p>
          If anyone is in immediate danger, contact local emergency services
          first. {brand.name} Support is not an emergency responder. After you
          are safe, file a report so we can review platform-related risk.
        </p>
      </LegalSection>
    </>
  );
}
