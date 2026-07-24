import { brand } from "@/lib/brand";

import type { MarketingFaqItem } from "@/components/marketing/MarketingFaq";
import type { MarketingFeature } from "@/components/marketing/MarketingFeatureGrid";

export const FOR_FANS_PATH = "/for-fans";

export const forFansSeo = {
  title: "Discover Events on Pàdéyá — Tickets, Fan Passport, Fan Connect & More",
  description: `Find events near you, buy verified tickets, build a Fan Passport, and connect around the scene on ${brand.name}.`,
  path: FOR_FANS_PATH,
} as const;

export const forFansHero = {
  eyebrow: `For fans · ${brand.name}`,
  headline: "Find the moment. Keep the proof. Join the scene.",
  support:
    "Discover verified events, save your tickets, build your Fan Passport, and connect with people around the nights you attend.",
  trustLine: "Verified events · QR tickets · Fan Connect",
  primary: { href: "/events", label: "Explore events" },
  secondary: {
    href: "/register?next=/dashboard/passport",
    label: "Create Fan Passport",
  },
} as const;

/** Three major product pillars for homepage / benefits — not a docs checklist. */
export const forFansPillars: MarketingFeature[] = [
  {
    title: "Fan Passport",
    body: "Public-safe identity, badges, attended events, reviews, and privacy controls.",
    href: "/fans",
    linkLabel: null,
  },
  {
    title: "Fan Connect",
    body: "Meet people around shared events, interests, and nearby scenes — with controls you own.",
    href: "/connect",
    linkLabel: null,
  },
  {
    title: "Ambassador Rewards",
    body: "Share events you love and earn when approved campaigns are active.",
    href: "/ambassadors",
    linkLabel: null,
  },
];

/** Five stronger journey pillars — not a docs checklist. */
export const forFansBenefits: MarketingFeature[] = [
  {
    title: "Discover",
    body: "Browse nights near you, by category, followed hosts, and Pàdéyá Picks.",
    href: "/events",
    linkLabel: null,
  },
  {
    title: "Attend",
    body: "Secure checkout, signed QR at the door, and verified attendance that sticks.",
    href: "/dashboard/tickets",
    linkLabel: null,
  },
  {
    title: "Connect",
    body: "Optional Fan Connect around the same events — privacy, block, and report built in.",
    href: "/connect",
    linkLabel: null,
  },
  {
    title: "Build identity",
    body: "Fan Passport collects badges, reviews, and proof beyond a camera-roll screenshot.",
    href: "/fans",
    linkLabel: null,
  },
  {
    title: "Rewards",
    body: "Share Ambassador links and earn when campaigns are open and sales verify as paid.",
    href: "/ambassadors",
    linkLabel: null,
  },
];

export const forFansPassportPoints = [
  {
    title: "Badges & stamps",
    body: "Earn marks that reflect nights attended and activity over time.",
  },
  {
    title: "Verified nights",
    body: "Check-in feeds attendance so your history stays credible.",
  },
  {
    title: "Reviews you earned",
    body: "Share what the night was like after you were actually there.",
  },
  {
    title: "Privacy you control",
    body: "Choose what is public from Passport settings — visibility stays yours.",
  },
] as const;

export const forFansConnect: MarketingFeature[] = [
  {
    title: "Same-event people",
    body: "Find others going to the same nights — not a dating map or public attendee dump.",
  },
  {
    title: "Shared scene",
    body: "Suggestions from shared event context and interests you both care about.",
  },
  {
    title: "Nearby, privacy-safe",
    body: "Nearby discovery only where your settings allow — never forced exposure.",
  },
  {
    title: "Safety tools",
    body: "Block, report, message controls, plus Safety Center when you need escalation.",
    href: "/safety",
    linkLabel: "Safety Center",
  },
];

export const forFansTicketing: MarketingFeature[] = [
  {
    title: "Signed QR tickets",
    body: "Tickets issue after verified payment — present a signed QR hosts can trust at the door.",
  },
  {
    title: "Door check-in",
    body: "Staff scan with official check-in tools, including offline-friendly display when you need it.",
  },
  {
    title: "Verified attendance",
    body: "Check-in feeds Fan Passport proof so reviews and memories stay credible.",
  },
  {
    title: "Merch & drops",
    body: "Add event merch at checkout, catch post-event drops, and track orders in Personal → Merch.",
    href: "/merch-guide",
    linkLabel: "How merch works",
  },
  {
    title: "Refunds & support",
    body: "Clear paths through Refund Policy and Support when an event changes or you need help.",
    href: "/support",
    linkLabel: "Get support",
  },
];

export const forFansDiscovery: MarketingFeature[] = [
  {
    title: "Events near you",
    body: "Closest upcoming nights first — not a national feed that ignores your city.",
    href: "/events/near-me",
    linkLabel: "Near me",
  },
  {
    title: "Categories & vibe",
    body: "Music, nightlife, culture, and more — filter to how you actually go out.",
    href: "/events",
    linkLabel: "Browse events",
  },
  {
    title: "Hosts you follow",
    body: "Stay close to promoters and venues that already earned your trust.",
    href: "/hosts",
    linkLabel: "Browse hosts",
  },
  {
    title: "Pàdéyá Picks",
    body: "Curated standouts worth a second look on discovery and the homepage.",
    href: "/events",
  },
  {
    title: "City pages",
    body: "Local hubs so scenes are easy to browse without guessing.",
    href: "/events/city/lagos",
    linkLabel: "Explore Lagos",
  },
];

export const forFansRewards: MarketingFeature[] = [
  {
    title: "Ambassador campaigns",
    body: "Share eligible events with your link. Earnings attach only to verified paid referrals.",
    href: "/ambassadors",
    linkLabel: "How Ambassadors work",
  },
  {
    title: "Share the night",
    body: "Send event pages to friends — discovery travels better person-to-person.",
  },
  {
    title: "Honest rewards",
    body: "Campaign perks and leaderboards depend on the host’s rules — we don’t invent guarantees.",
  },
];

export const forFansFaqs: MarketingFaqItem[] = [
  {
    q: "How do I buy tickets?",
    a: "Open an event page, choose a ticket type, and complete checkout. Your ticket appears in Personal → Tickets after payment is verified.",
  },
  {
    q: "Where do I find my ticket?",
    a: "Go to Personal → Tickets. Your signed QR is there for door scan — including offline-friendly display when available.",
  },
  {
    q: "What is Fan Passport?",
    a: "Your fan identity on Pàdéyá — attended nights, badges, follows, and reviews you choose to show. Manage visibility from Passport settings.",
  },
  {
    q: "What is Fan Connect?",
    a: "Optional connections around events. It is not dating or a public attendee dump — privacy rules apply, and you control who can reach you.",
  },
  {
    q: "Can I control who sees my profile?",
    a: "Yes. Passport settings let you control public visibility. Fan Connect and messaging have separate controls for requests and contact.",
  },
  {
    q: "How do refunds work?",
    a: "Refunds depend on event status and policy. Start from Personal → Refunds or read the Refund Policy, and include your order reference in Support if you need help.",
  },
  {
    q: "Can I buy merch with my tickets?",
    a: "Yes when a host attaches merch to an event. You may also see post-event drops or Vault exclusives. Orders live in Personal → Merch — see the Merch page for formats.",
  },
  {
    q: "How do I contact support?",
    a: "Open the Support Center to create a ticket or look up an existing one. Safety issues can also go through Report and the Safety Center.",
  },
];

export const forFansFinalCta = {
  title: "Find the moment. Keep the proof.",
  description:
    "Explore what’s happening around you — or create a Fan Passport and start collecting the proof.",
  primary: { href: "/events", label: "Explore events" },
  secondary: {
    href: "/register?next=/dashboard/passport",
    label: "Create Fan Passport",
  },
} as const;

export const FOR_FANS_CTA_HREFS = [
  "/events",
  "/register?next=/dashboard/passport",
  "/support",
  "/fans",
  "/connect",
  "/dashboard/passport",
  "/hosts",
  "/merch",
  "/blog",
  "/safety",
  "/ambassadors",
] as const;
