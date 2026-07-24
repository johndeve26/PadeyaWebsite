/** Support topic guidance — Help articles + self-service before tickets. */

export type SupportTopicConfig = {
  value: string;
  label: string;
  explanation: string;
  quickAnswers: string[];
  selfService: { href: string; label: string; roles?: Array<"guest" | "fan" | "host"> }[];
  safetyWarning?: string;
  fallbackArticleSlugs: string[];
};

export const SUPPORT_TOPIC_GUIDES: SupportTopicConfig[] = [
  {
    value: "account_login",
    label: "Account / login",
    explanation:
      "Sign-in, password resets, sessions, and account access issues.",
    quickAnswers: [
      "Use a unique password and sign out of shared devices after desk shifts.",
      "If you suspect unauthorized access, change your password and review Settings.",
      "Restrictions and suspensions have a separate appeals path.",
    ],
    selfService: [
      { href: "/login", label: "Sign in", roles: ["guest"] },
      { href: "/dashboard/settings", label: "Account settings", roles: ["fan", "host"] },
      { href: "/help/articles/login-and-account-security", label: "Security guide" },
    ],
    fallbackArticleSlugs: [
      "login-and-account-security",
      "how-to-appeal-restriction",
    ],
  },
  {
    value: "tickets_orders",
    label: "Tickets / orders",
    explanation:
      "Finding QR tickets, guest checkout, buying for someone else, and order access.",
    quickAnswers: [
      "Tickets issue only after verified payment — not on chat screenshots.",
      "Signed-in buyers open My Tickets; guests recover with the checkout email.",
      "Door staff scan signed QRs — photo-only proof is not enough.",
    ],
    selfService: [
      { href: "/dashboard/tickets", label: "My tickets", roles: ["fan", "host"] },
      { href: "/dashboard/orders", label: "My orders", roles: ["fan", "host"] },
      { href: "/support/tickets/lookup", label: "Track a ticket" },
      { href: "/ticket-policy", label: "Ticket Policy" },
    ],
    fallbackArticleSlugs: [
      "how-to-find-your-qr-ticket",
      "how-guest-checkout-works",
      "how-to-buy-ticket-for-someone-else",
      "how-to-buy-tickets",
    ],
  },
  {
    value: "payments_refunds",
    label: "Payments / refunds",
    explanation:
      "Secure checkout, pending charges, refund requests, and fee questions.",
    quickAnswers: [
      "Pending payments mean the provider is still confirming — tickets wait for verification.",
      "Refund eligibility follows host rules plus the Refund Policy.",
      "Include your order or payment reference when contacting Support.",
    ],
    selfService: [
      { href: "/dashboard/orders", label: "My orders", roles: ["fan", "host"] },
      { href: "/dashboard/refunds", label: "Refund requests", roles: ["fan", "host"] },
      { href: "/refund-policy", label: "Refund Policy" },
      { href: "/support/tickets/lookup", label: "Track a ticket" },
    ],
    fallbackArticleSlugs: [
      "how-refunds-work",
      "how-payments-work",
      "how-padeya-fees-and-host-earnings-work",
    ],
  },
  {
    value: "event_issue",
    label: "Event issue",
    explanation:
      "Listing details, venue timing, cancellations, and night-of problems.",
    quickAnswers: [
      "Hosts are responsible for listing accuracy and communicating changes.",
      "Check the official event page and your order email for updates.",
      "Safety emergencies belong with local authorities first.",
    ],
    selfService: [
      { href: "/events", label: "Browse events" },
      { href: "/dashboard/orders", label: "My orders", roles: ["fan", "host"] },
      { href: "/safety", label: "Safety Center" },
    ],
    fallbackArticleSlugs: ["find-events-on-padeya", "how-refunds-work"],
  },
  {
    value: "host_issue",
    label: "Host issue",
    explanation:
      "Publishing events, ticket inventory, QR check-in, and host team access.",
    quickAnswers: [
      "Publish refund and ticket policies before selling.",
      "Use host desk tools to scan signed QRs — don’t accept chat screenshots.",
      "Invite staff with roles instead of sharing your password.",
    ],
    selfService: [
      { href: "/host", label: "Host dashboard", roles: ["host"] },
      { href: "/host/support", label: "Host support", roles: ["host"] },
      { href: "/host/desk", label: "Tickets & Entry", roles: ["host"] },
      { href: "/host/onboarding", label: "Become a host", roles: ["guest", "fan"] },
    ],
    fallbackArticleSlugs: [
      "create-your-first-event",
      "how-qr-check-in-works",
      "how-hosts-add-team-members",
      "how-to-become-a-host",
    ],
  },
  {
    value: "merch",
    label: "Merch",
    explanation: "Merch orders, pickup windows, and post-event drops.",
    quickAnswers: [
      "Fulfilment starts after verified payment.",
      "Follow the host’s pickup or shipping notes on the order.",
      "Merch refunds follow host rules and the Refund Policy.",
    ],
    selfService: [
      { href: "/dashboard/orders", label: "My orders", roles: ["fan", "host"] },
      { href: "/refund-policy", label: "Refund Policy" },
    ],
    fallbackArticleSlugs: [
      "how-merch-and-post-event-drops-work",
      "how-vault-content-works",
    ],
  },
  {
    value: "fan_connect",
    label: "Fan Connect",
    explanation:
      "Suggestions, privacy controls, and meeting people around shared nights.",
    quickAnswers: [
      "Suggestions use shared events and interests you opt into.",
      "Tighten visibility in privacy and Connect settings anytime.",
      "Block or report anyone who crosses the line.",
    ],
    selfService: [
      { href: "/connect", label: "Fan Connect" },
      { href: "/dashboard/settings", label: "Privacy settings", roles: ["fan", "host"] },
      { href: "/safety", label: "Safety Center" },
    ],
    fallbackArticleSlugs: [
      "how-fan-connect-suggestions-work",
      "how-to-create-fan-passport",
      "how-to-block-or-report-someone",
    ],
  },
  {
    value: "messaging_abuse",
    label: "Messaging / report abuse",
    explanation: "Harassment, scams, and unsafe messages.",
    quickAnswers: [
      "Block first, then report with message or profile references.",
      "Never share OTPs, passwords, or off-platform payment instructions.",
      "Pàdéyá Support cannot replace emergency services.",
    ],
    selfService: [
      { href: "/dashboard/messages", label: "Messages", roles: ["fan", "host"] },
      { href: "/safety", label: "Safety Center" },
      { href: "/report", label: "Report page" },
    ],
    safetyWarning:
      "If there is immediate danger, contact local authorities first.",
    fallbackArticleSlugs: [
      "how-to-block-or-report-someone",
      "messaging-on-padeya",
    ],
  },
  {
    value: "sponsorship",
    label: "Sponsorship",
    explanation: "Brand inquiries, deliverables, and sponsorship request status.",
    quickAnswers: [
      "Send clear goals and budget ranges with your inquiry.",
      "Hosts remain responsible for on-site activations they agree to.",
      "Keep negotiations and status on-platform when possible.",
    ],
    selfService: [
      { href: "/sponsorships", label: "Sponsors" },
      { href: "/hosts", label: "Browse hosts" },
    ],
    fallbackArticleSlugs: ["how-sponsorship-inquiries-work"],
  },
  {
    value: "ambassador",
    label: "Ambassador",
    explanation: "Campaigns, tracked links/codes, conversions, and rewards.",
    quickAnswers: [
      "Share only your tracked link or code for the campaign.",
      "Rewards follow the campaign’s published rules and payout timing.",
      "Hosts set commission rules and monitor for abuse.",
    ],
    selfService: [
      { href: "/ambassadors", label: "Ambassadors" },
      { href: "/help/articles/how-ambassador-campaigns-work", label: "Campaign guide" },
    ],
    fallbackArticleSlugs: ["how-ambassador-campaigns-work"],
  },
  {
    value: "technical",
    label: "Technical issue",
    explanation: "Bugs, loading errors, and unexpected website behaviour.",
    quickAnswers: [
      "Try a refresh, another browser, or signing out and back in.",
      "Note the page URL and what you tapped when it failed.",
      "Screenshots help — avoid including passwords or payment secrets.",
    ],
    selfService: [
      { href: "/help", label: "Help Center" },
      { href: "/dashboard/settings", label: "Account settings", roles: ["fan", "host"] },
    ],
    fallbackArticleSlugs: [
      "how-to-contact-support",
      "login-and-account-security",
    ],
  },
  {
    value: "other",
    label: "Other",
    explanation: "Anything else — we’ll still try Help articles first.",
    quickAnswers: [
      "Search Help for tickets, refunds, hosting, Fan Passport, or checkout.",
      "Include references (order, event, ticket number) if you open a ticket.",
    ],
    selfService: [
      { href: "/help", label: "Browse Help Center" },
      { href: "/faq", label: "Browse FAQs" },
      { href: "/support/tickets/lookup", label: "Track a ticket" },
    ],
    fallbackArticleSlugs: ["how-to-contact-support"],
  },
];

export function getSupportTopicGuide(value: string): SupportTopicConfig | undefined {
  return SUPPORT_TOPIC_GUIDES.find((t) => t.value === value);
}
