import { brand } from "@/lib/brand";

import type { MarketingFaqItem } from "@/components/marketing/MarketingFaq";

export const FOR_HOSTS_PATH = "/for-hosts";

export const forHostsSeo = {
  title: "Host Events on Pàdéyá — Ticketing, QR Check-in, Merch & Growth Tools",
  description: `Create events, sell verified tickets, run QR check-in, grow with Ambassadors and sponsorships, and build your Host Legacy on ${brand.name}.`,
  path: FOR_HOSTS_PATH,
} as const;

export const forHostsHero = {
  eyebrow: `For hosts · ${brand.name}`,
  headline: "Create the night. Own the door. Grow the audience.",
  support:
    "Event Studio, verified ticketing, QR check-in, audience tools, and a public Legacy — one workspace from flyer to packed door.",
  trustLine: "Verified payments · Signed QR · Host Legacy",
  primary: { href: "/host/events/new", label: "Create event" },
  secondary: { href: "#host-tools", label: "Explore host tools" },
} as const;

export type HostAudience = {
  title: string;
  body: string;
};

export const forHostsAudiences: HostAudience[] = [
  {
    title: "Promoters",
    body: "List nights, sell tiers, and track sell-through without juggling three apps.",
  },
  {
    title: "Venues & clubs",
    body: "Door QR scanning and staff-ready entry workflows for busy nights.",
  },
  {
    title: "Artists & creators",
    body: "Own the ticket page, merch drop, and Legacy fans follow between shows.",
  },
  {
    title: "Communities & brands",
    body: "Publish gatherings, run sponsorships, and keep verified reviews on your profile.",
  },
];

export type HostToolCategory = {
  title: string;
  body: string;
  items: readonly string[];
};

export const forHostsToolCategories: HostToolCategory[] = [
  {
    title: "Create & sell",
    body: "Event Studio to verified checkout — listings, tiers, and capacity in one flow.",
    items: ["Event Studio", "Ticket types", "Verified checkout"],
  },
  {
    title: "Run the door",
    body: "Staff-ready entry when the line is moving — signed QR, guest lists, scanner roles.",
    items: ["QR check-in", "Guest entry", "Staff roles"],
  },
  {
    title: "CRM & audience",
    body: "Followers, announcements, and attendance-backed reviews after the lights come up.",
    items: ["Audience CRM", "Announcements", "Verified reviews"],
  },
  {
    title: "Merch, Vault & growth",
    body: "Stack revenue and reach beyond the ticket — merch, Vault, Ambassadors, sponsors.",
    items: ["Merch", "Vault", "Ambassadors", "Sponsorships"],
  },
  {
    title: "Analytics & team",
    body: "See what sold, who worked the door, and where to ask for help.",
    items: ["Analytics", "Team management", "Host support"],
  },
];

export const forHostsWorkflow = [
  {
    id: "profile",
    label: "Create host profile",
    description: "Onboard your workspace, brand, and public presence.",
  },
  {
    id: "event",
    label: "Build the event",
    description: "Event Studio covers media, details, and ticket tiers.",
  },
  {
    id: "publish",
    label: "Publish & promote",
    description: "Go live on discovery, Ambassadors, and sponsorships.",
  },
  {
    id: "door",
    label: "Check in guests",
    description: "Scan signed QR codes at the door with your team.",
  },
  {
    id: "grow",
    label: "Review & grow",
    description: "Analytics, CRM, Legacy, Vault, and the next sell-out.",
  },
] as const;

export type HostTrustItem = {
  title: string;
  body: string;
};

export const forHostsTicketing: HostTrustItem[] = [
  {
    title: "Verified ticketing",
    body: "Tickets issue after payment confirmation — frontend “success” is never enough.",
  },
  {
    title: "Ticket types",
    body: "General, VIP, early bird, free, and capacity-aware tiers per event.",
  },
  {
    title: "QR check-in",
    body: "Signed payloads for staff scanning — including offline-friendly foundations.",
  },
  {
    title: "Guest entry",
    body: "Manage attendees, scans, and entry status from host event tools.",
  },
];

export type HostGrowthItem = {
  title: string;
  body: string;
  href?: string;
  linkLabel?: string;
};

export const forHostsGrowth: HostGrowthItem[] = [
  {
    title: "Ambassador campaigns",
    body: "Turn loyal fans into promoters with tracked links and rewards on verified paid sales.",
    href: "/ambassadors/how-it-works",
    linkLabel: "How it works",
  },
  {
    title: "Sponsorship inquiries",
    body: "List packages on the sponsorship marketplace and manage brand interest from Host tools.",
    href: "/sponsorships/hosts",
    linkLabel: "For host sponsors",
  },
  {
    title: "Audience CRM",
    body: "Followers and announcements so your next night starts warmer than a cold flyer.",
  },
  {
    title: "Legacy Page",
    body: "A public host page that compounds reputation across every event you run.",
    href: "/hosts",
    linkLabel: "Browse hosts",
  },
  {
    title: "Vault",
    body: "Exclusive content and unlocks that deepen the relationship after check-in.",
  },
  {
    title: "Merch",
    body: "Physical proof of the night — sold with tickets or as follow-up drops.",
    href: "/merch-guide",
    linkLabel: "How merch works",
  },
];

export const forHostsFees = {
  title: "Fees when you sell — not for an empty calendar",
  lead: "Fees are shown before you publish or sell.",
  body: `${brand.name} is free for fans to join. Hosts pay platform fees on successful sales. Live rates appear on Pricing and in your host finance views — we do not invent exact percentages here.`,
  cta: { href: "/pricing", label: "View pricing" },
} as const;

export const forHostsFaqs: MarketingFaqItem[] = [
  {
    q: "How do I create an event?",
    a: "Start host onboarding (or open Host workspace if you already host), then use Create event / Event Studio. Add details, ticket types, and publish when ready. Fees and totals appear in the host flow before you go live and at checkout for buyers.",
  },
  {
    q: "Can I manage my team?",
    a: "Yes. Invite teammates from Host → Team with role-based access so scanners and ops staff get only what they need.",
  },
  {
    q: "Can I scan tickets?",
    a: "Yes. Each paid ticket carries a signed QR for door check-in. Use the event check-in tools with your staff accounts.",
  },
  {
    q: "Can I sell merch?",
    a: "Yes. Merch Studio lets you sell event add-ons, standalone products, post-event drops, and Vault exclusives, plus manage pickup fulfillment. See the Merch page for formats and the full host flow.",
  },
  {
    q: "Can I get sponsors?",
    a: "Yes. Create sponsorship packages and appear in the sponsorship marketplace so brands can inquire. Manage inquiries from Host → Sponsorships.",
  },
  {
    q: "Can I use ambassadors?",
    a: "Yes. Launch Ambassador campaigns so fans can promote with tracked links. Commission and rewards only attach to verified paid sales.",
  },
  {
    q: "How do payouts work?",
    a: "Successful sales settle through the platform payout flow with ledger visibility in Host finance tools. Exact fee rates are shown in pricing/host finance views — we do not invent rates on this page.",
  },
  {
    q: "Can I contact support?",
    a: "Yes. Open the Support Center for host-related tickets, or use Host → Support from your workspace. Safety and policy pages are also public.",
  },
];

export const forHostsFinalCta = {
  title: "Ready to host on Pàdéyá?",
  description:
    "Create your next event, finish host onboarding, or talk to Support if you need a hand with a bigger run of nights.",
  primary: { href: "/host/events/new", label: "Create event" },
  secondary: { href: "/host/onboarding", label: "Start host onboarding" },
  tertiary: { href: "/support", label: "Contact support" },
} as const;

/** Canonical CTA hrefs used by smoke / unit checks. */
export const FOR_HOSTS_CTA_HREFS = [
  "/host/events/new",
  "#host-tools",
  "/host/onboarding",
  "/support",
  "/pricing",
  "/hosts",
  "/events",
  "/merch",
  "/blog",
  "/safety",
  "/sponsorships",
  "/ambassadors",
] as const;
