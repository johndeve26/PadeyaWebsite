import { brand } from "@/lib/brand";

import type { MarketingFaqItem } from "@/components/marketing/MarketingFaq";
import type { MarketingFeature } from "@/components/marketing/MarketingFeatureGrid";

/** Marketplace shop (catalog, drops, Vault teasers). */
export const MERCH_PATH = "/merch";

/** Educational / resource guide (formats, how it works, fees, policies). */
export const MERCH_GUIDE_PATH = "/merch-guide";

export const merchSeo = {
  title: "Shop merch on Pàdéyá — Host shops, drops & Vault exclusives",
  description: `Discover host merch, event add-ons, post-event drops, and Vault exclusives from ${brand.name} hosts. Shop the night. Wear the memory.`,
  path: MERCH_PATH,
} as const;

export const merchGuideSeo = {
  title: "Merch that moves with the moment — How merch works on Pàdéyá",
  description: `Learn how merch works on ${brand.name}: event add-ons, host shops, post-event drops, Vault exclusives, pickup, fees, and policies.`,
  path: MERCH_GUIDE_PATH,
} as const;

export const merchHero = {
  eyebrow: `Merch · ${brand.name}`,
  headline: "Merch that moves with the moment",
  support:
    "Event add-ons, host shops, post-event drops, and Vault exclusives — how fans buy and hosts sell on Pàdéyá.",
  trustLine: "Formats · Drops · Pickup · Fees · Policies",
  primary: { href: MERCH_PATH, label: "Shop merch" },
  secondary: { href: "#how-it-works", label: "How it works" },
} as const;

export const merchFansPoints: MarketingFeature[] = [
  {
    title: "Buy on events",
    body: "Fans can buy merch attached to events from the event experience and host storefront flow.",
    href: "/events",
    linkLabel: "Browse events",
  },
  {
    title: "Checkout add-ons",
    body: "Eligible products may appear during ticket checkout so you can bundle shirts, vouchers, or drops with your tickets.",
  },
  {
    title: "Post-event drops",
    body: "After the night, hosts may release limited merch for checked-in fans, ticket buyers, VIPs, or Vault members.",
  },
  {
    title: "Vault unlock",
    body: "Vault-exclusive merch may require unlocking Vault access before you can purchase.",
    href: "/dashboard/vault",
    linkLabel: "Open Vault",
  },
  {
    title: "Orders in your dashboard",
    body: "Merch orders appear in your personal dashboard so you can track status and details in one place.",
    href: "/dashboard/merchandise",
    linkLabel: "My merch",
  },
  {
    title: "Pickup instructions",
    body: "When hosts share pickup or fulfillment details, those instructions show with your order when available.",
  },
];

export const merchHostsPoints: MarketingFeature[] = [
  {
    title: "Create products",
    body: "Build merch products in Merch Studio with pricing, variants, and inventory you control.",
    href: "/host/merchandise",
    linkLabel: "Open Merch Studio",
  },
  {
    title: "Attach to events",
    body: "Link products to an event so fans discover them on the event page and at checkout.",
    href: "/host/events",
    linkLabel: "Host events",
  },
  {
    title: "Sell standalone",
    body: "Offer host-branded products that are not tied to a single night.",
  },
  {
    title: "Post-event drops",
    body: "Release limited merch after the event to eligible fans based on attendance, tickets, VIP, or Vault rules.",
  },
  {
    title: "Vault-exclusive",
    body: "Reward paid Vault members with exclusive products or early access.",
  },
  {
    title: "Fulfillment tools",
    body: "Manage inventory, pricing, pickup notes, and fulfillment status from the host workspace.",
    href: "/for-hosts",
    linkLabel: "For hosts",
  },
];

export const merchFormats: MarketingFeature[] = [
  {
    title: "Event add-ons",
    body: "Sell shirts, wristbands, masks, caps, drink vouchers, or bundles during ticket checkout.",
  },
  {
    title: "Standalone merch",
    body: "Sell host-branded products even when they are not tied to a single event.",
  },
  {
    title: "Post-event drops",
    body: "Release limited merch after the event to checked-in fans, ticket buyers, VIPs, or Vault members.",
  },
  {
    title: "Vault-exclusive merch",
    body: "Reward paid Vault members with exclusive products or early access.",
  },
  {
    title: "Pickup / fulfillment",
    body: "Share pickup notes, venue collection details, or fulfillment instructions.",
  },
];

export const merchWorkflow = [
  {
    id: "create",
    label: "Host creates merch",
    description: "Add a product in Merch Studio with media, variants, and pricing.",
  },
  {
    id: "type",
    label: "Host chooses product type",
    description: "Pick event add-on, standalone, post-event drop, Vault exclusive, or fulfillment-ready.",
  },
  {
    id: "link",
    label: "Host links it to an event or makes it standalone",
    description: "Attach to a night for checkout visibility, or sell on the host storefront alone.",
  },
  {
    id: "buy",
    label: "Fan buys merch",
    description: "Fans purchase from the event, checkout add-ons, host page, Vault, or a drop link.",
  },
  {
    id: "pay",
    label: "Payment is confirmed",
    description: "Orders settle through verified payment — frontend success alone is never enough.",
  },
  {
    id: "fulfill",
    label: "Host fulfills or marks pickup",
    description: "Hosts update fulfillment status and share pickup or delivery instructions.",
  },
  {
    id: "track",
    label: "Fan tracks merch in dashboard",
    description: "Buyers follow orders, pickup notes, and status from Personal → Merch.",
  },
] as const;

export const merchWherePoints: MarketingFeature[] = [
  {
    title: "Event detail page",
    body: "Eligible products appear alongside the night so fans can browse before buying tickets.",
  },
  {
    title: "Checkout add-ons",
    body: "Fans can add merch while completing ticket checkout when the host has attached products.",
  },
  {
    title: "Host public page",
    body: "Standalone and host-storefront merch can surface on the host’s public presence.",
    href: "/hosts",
    linkLabel: "Browse hosts",
  },
  {
    title: "Vault page",
    body: "Vault-exclusive products live with unlock rules so members see what they have earned.",
  },
  {
    title: "Post-event drop notification",
    body: "Eligible fans may be notified when a host releases a post-event drop.",
  },
  {
    title: "Fan dashboard",
    body: "Orders, pickup details, and status live in Personal → Merch.",
    href: "/dashboard/merchandise",
    linkLabel: "My merch",
  },
  {
    title: "Host merch workspace",
    body: "Hosts create, price, inventory, and fulfill from Merch Studio and event tools.",
    href: "/host/merchandise",
    linkLabel: "Merch Studio",
  },
];

export const merchNotificationsPoints: MarketingFeature[] = [
  {
    title: "Admin-controlled merch alerts",
    body: "Platform admins can control whether merch notification types are enabled across Pàdéyá.",
  },
  {
    title: "Host drop notify",
    body: "Hosts may notify eligible fans when a post-event drop goes live.",
  },
  {
    title: "New listing alerts",
    body: "Notifications for new merch listings depend on admin settings and what the host publishes.",
  },
  {
    title: "Preference respect",
    body: "Where notification preferences apply, Pàdéyá respects what users have opted into.",
  },
];

export const merchFeesPoints: MarketingFeature[] = [
  {
    title: "Platform fees may apply",
    body: "Merch sales may include platform fees or commission configured by admin — we do not invent percentages here.",
  },
  {
    title: "Buyer fees at checkout",
    body: "Buyer fees may apply depending on admin settings and are shown before payment.",
  },
  {
    title: "Host earnings clarity",
    body: "Hosts can view gross sales, deductions, and net earnings in host finance and earnings views.",
    href: "/pricing",
    linkLabel: "View pricing",
  },
];

export const merchPoliciesPoints: MarketingFeature[] = [
  {
    title: "Host responsibility",
    body: "Hosts are responsible for product accuracy, pickup details, fulfillment, and availability.",
  },
  {
    title: "Platform & support tools",
    body: `${brand.name} provides the marketplace, payments rails, and support tools — not the physical product itself.`,
  },
  {
    title: "Refunds & returns",
    body: "Refunds and returns depend on policy and host rules for the product and fulfillment state.",
    href: "/refund-policy",
    linkLabel: "Refund Policy",
  },
  {
    title: "Get help",
    body: "Contact Support for merch issues, or browse Help for guides on orders, drops, and pickup.",
    href: "/help",
    linkLabel: "Help Center",
  },
];

export const merchFaqs: MarketingFaqItem[] = [
  {
    q: "Can I buy merch without buying a ticket?",
    a: "Sometimes. Standalone host merch and some storefront products do not require a ticket. Event add-ons and eligibility-gated drops may require a ticket, attendance, VIP, or Vault access — the product page shows what applies.",
  },
  {
    q: "Can merch be attached to an event?",
    a: "Yes. Hosts can attach merch to events so fans buy night-related products from the event page and during checkout.",
  },
  {
    q: "What is a post-event merch drop?",
    a: "A limited release after the event for eligible fans — such as checked-in attendees, ticket buyers, VIPs, or Vault members — when the host publishes the drop.",
  },
  {
    q: "What is Vault-exclusive merch?",
    a: "Merch reserved for fans who unlock Vault access under the host’s rules. Teasers may be public; purchase can stay gated until access is granted.",
  },
  {
    q: "Where do I find my merch order?",
    a: "Open Personal → Merch in your dashboard. Orders, pickup notes, and status appear there after payment is confirmed.",
  },
  {
    q: "How does pickup work?",
    a: "When a host offers pickup, instructions and any pickup QR or notes appear with your order. Bring what the host asks for (order reference, ID, or QR) to the collection point.",
  },
  {
    q: "Can I get a refund for merch?",
    a: "It depends on fulfilment status, host rules, and the Refund Policy. Start from Personal → Refunds or Support with your order reference.",
  },
  {
    q: "Can hosts sell standalone merch?",
    a: "Yes. Hosts can sell products that are not tied to a single event from Merch Studio and their public host presence.",
  },
  {
    q: "Can hosts manage inventory?",
    a: "Yes. Hosts manage inventory, pricing, variants, pickup notes, and fulfillment status from the host merch workspace.",
  },
  {
    q: "Are merch fees different from ticket fees?",
    a: "They can be. Merch may use separate fee settings from tickets. Live rates appear on Pricing and in host finance views — we do not hardcode percentages on this page.",
  },
];

export const merchFinalCta = {
  title: "Ready to sell or shop the drop?",
  description:
    "Browse the marketplace, open Merch Studio as a host, or explore events with merch add-ons.",
  primary: { href: MERCH_PATH, label: "Shop merch" },
  secondary: { href: "/host/merchandise", label: "Create merch as a host" },
  tertiary: { href: "/events", label: "Explore events" },
} as const;
