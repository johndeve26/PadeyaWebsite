import Link from "next/link";

import { brand } from "@/lib/brand";
import type { PublicPricingFeeRow } from "@/lib/types/pricing";

export const PRICING_TIERS = [
  {
    name: "Fans",
    price: "Free to join",
    blurb:
      "Browse events, create an account, and use Fan Passport and Fan Connect at no cost unless future paid features are added.",
    points: [
      "Browsing events is free",
      "Creating a fan account is free",
      "Fan Passport and Fan Connect are free today",
      "Pay only what checkout shows for tickets, merch, or Vault",
    ],
  },
  {
    name: "Hosts",
    price: "Fee on sales",
    blurb:
      "Creating a host profile can be free unless configured otherwise. Pàdéyá may charge commission when tickets, merch, or Vault sell.",
    points: [
      "Host-paid fees are deducted from host earnings",
      "See estimated net in Host earnings / finance",
      "Exact fees may vary by host, volume, or agreement",
      "Order fee snapshots preserve terms at time of sale",
    ],
  },
  {
    name: "High volume",
    price: "Custom",
    blurb:
      "Festivals, venues, brands, schools, churches, communities, and high-volume hosts may receive custom rates.",
    points: [
      "Volume-based commercial conversations",
      "Custom terms shown in host finance when configured",
      "Priority onboarding paths",
      "Contact support or sales to start",
    ],
  },
] as const;

export const PRICING_FAQ = [
  {
    q: "Is Pàdéyá free for fans?",
    a: "Yes. Browsing events and creating a fan account are free. Fan Passport and Fan Connect are free unless future paid features are added. You only pay for purchases you choose, plus any buyer fees shown at checkout.",
  },
  {
    q: "Do I need an account to buy tickets?",
    a: "Guest checkout may be available for some events. An account helps you manage tickets, refunds, Fan Passport, and support. Checkout always shows your final total before payment.",
  },
  {
    q: "What fees do buyers pay?",
    a: "Buyers pay the ticket, merch, or Vault prices shown at checkout. A buyer platform/service fee may apply, and payment processing fees may apply depending on configuration. Buyer fees are shown before you pay.",
  },
  {
    q: "What fees do hosts pay?",
    a: "Hosts typically pay Pàdéyá commission and any host-paid fixed or processing fees on successful sales. Those amounts are deducted from host earnings — they are not shown as host commercial rates on the buyer checkout screen.",
  },
  {
    q: "Can different hosts have different fees?",
    a: "Yes. Fee settings can differ by host, volume, product type, or commercial agreement. The public pricing page says rates may vary; each host sees their own exact terms in Host earnings / finance.",
  },
  {
    q: "Where do hosts see net earnings?",
    a: "Open Host → Earnings (and related finance / payouts views). You will see gross sales, Pàdéyá deductions, and net after host-paid fees, refunds, and ambassador rewards where applicable.",
  },
  {
    q: "Are fees refundable?",
    a: "Approved refunds follow the Refund Policy. Some partner or platform fees may be non-recoverable on reversal, so refunded amounts may reflect what can be returned through the original payment path.",
  },
  {
    q: "Are payment processing fees included?",
    a: "Processing fees may apply depending on configuration. Buyer-paid processing appears at checkout; host-paid processing reduces host net. Exact lines are visible before payment or in host finance tools.",
  },
  {
    q: "Can high-volume hosts get custom pricing?",
    a: "Yes. Festivals, venues, brands, schools, churches, communities, and high-volume hosts may receive custom rates. Contact support or sales; configured terms appear in host finance tools.",
  },
  {
    q: "Are merch fees different from ticket fees?",
    a: "They can be. Merch may use separate fee settings from tickets. Live rates appear on this Pricing page and in host finance views — see the Merch page for how products sell.",
  },
] as const;

export const HOST_NET_FORMULA_LINES = [
  "sales subtotal",
  "− discounts",
  "− Pàdéyá host commission",
  "− host-paid processing fees",
  "− refunds/chargebacks",
  "− ambassador rewards where applicable",
] as const;

export const FALLBACK_FEE_CATEGORIES: PublicPricingFeeRow[] = [
  {
    fee_key: "category_ticket_sales",
    label: "Ticket sales",
    category: "ticket",
    payer: "host",
    fee_type: null,
    public_description:
      "Pàdéyá may charge host commission and/or fixed fees on successful ticket sales. Deducted from host earnings.",
    appears_at: ["host_earnings", "admin_finance"],
    configurable: true,
    may_vary_by_host: true,
    rates_public: false,
    enabled: true,
    percentage_value: null,
    fixed_value_major: null,
    currency: "NGN",
    display_rate: "May vary",
  },
  {
    fee_key: "category_merch_sales",
    label: "Merch sales",
    category: "merch",
    payer: "host",
    fee_type: null,
    public_description:
      "Merch commissions and host-paid fixed fees are deducted from host earnings when merch sells.",
    appears_at: ["host_earnings", "admin_finance"],
    configurable: true,
    may_vary_by_host: true,
    rates_public: false,
    enabled: true,
    percentage_value: null,
    fixed_value_major: null,
    currency: "NGN",
    display_rate: "May vary",
  },
  {
    fee_key: "category_vault_sales",
    label: "Vault sales",
    category: "vault",
    payer: "host",
    fee_type: null,
    public_description:
      "Vault unlock commissions are deducted from host earnings when configured.",
    appears_at: ["host_earnings", "admin_finance"],
    configurable: true,
    may_vary_by_host: true,
    rates_public: false,
    enabled: true,
    percentage_value: null,
    fixed_value_major: null,
    currency: "NGN",
    display_rate: "May vary",
  },
  {
    fee_key: "category_buyer_service",
    label: "Buyer platform / service fee",
    category: "general",
    payer: "buyer",
    fee_type: null,
    public_description:
      "Buyer platform fee is paid by the buyer. Shown at checkout before payment.",
    appears_at: ["checkout", "admin_finance"],
    configurable: true,
    may_vary_by_host: true,
    rates_public: false,
    enabled: true,
    percentage_value: null,
    fixed_value_major: null,
    currency: "NGN",
    display_rate: "Shown at checkout",
  },
  {
    fee_key: "category_payment_processing",
    label: "Payment / fiat processing fee",
    category: "payment",
    payer: "buyer",
    fee_type: null,
    public_description:
      "Processing fees may apply depending on configuration (buyer, host, or platform-absorbed).",
    appears_at: ["checkout", "host_earnings", "admin_finance"],
    configurable: true,
    may_vary_by_host: true,
    rates_public: false,
    enabled: true,
    percentage_value: null,
    fixed_value_major: null,
    currency: "NGN",
    display_rate: "May vary",
  },
  {
    fee_key: "category_refund",
    label: "Refund handling",
    category: "refund",
    payer: "buyer",
    fee_type: null,
    public_description:
      "Refund handling follows the Refund Policy. Some fees may be non-recoverable on reversal.",
    appears_at: ["checkout", "admin_finance"],
    configurable: true,
    may_vary_by_host: true,
    rates_public: false,
    enabled: true,
    percentage_value: null,
    fixed_value_major: null,
    currency: "NGN",
    display_rate: "Policy-based",
  },
  {
    fee_key: "category_high_volume",
    label: "High-volume / custom host agreements",
    category: "general",
    payer: "host",
    fee_type: null,
    public_description:
      "Festivals, venues, brands, schools, churches, communities, and high-volume hosts may receive custom rates.",
    appears_at: ["host_earnings", "admin_finance"],
    configurable: true,
    may_vary_by_host: true,
    rates_public: false,
    enabled: true,
    percentage_value: null,
    fixed_value_major: null,
    currency: "NGN",
    display_rate: "Custom",
  },
];

const APPEARS_LABEL: Record<string, string> = {
  checkout: "Checkout",
  host_earnings: "Host earnings",
  admin_finance: "Admin finance",
};

export function formatAppearsAt(values: string[]): string {
  return values.map((v) => APPEARS_LABEL[v] ?? v).join(" · ");
}

export function payerLabel(payer: string): string {
  if (payer === "buyer") return "Buyer";
  if (payer === "host") return "Host";
  if (payer === "platform") return "Platform";
  return payer;
}

export function PricingPlatformRelationship() {
  return (
    <section
      id="platform-relationship"
      className="rounded-[var(--radius-lg)] border border-border bg-card/70 p-6 dark:bg-surface-elevated"
    >
      <h2 className="font-display text-xl font-extrabold text-heading sm:text-2xl">
        Platform relationship
      </h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
        <p>
          {brand.name} is a platform and marketplace for discovery, ticketing,
          and host tools. Independent hosts create and operate their events.
        </p>
        <p>
          Unless stated otherwise, {brand.name} is not the event organizer.
          Hosts remain responsible for event operation, venue readiness, safety,
          and entry rules.
        </p>
        <p>
          Details live in{" "}
          <Link href="/terms" className="font-semibold text-primary">
            Terms
          </Link>
          ,{" "}
          <Link href="/ticket-policy" className="font-semibold text-primary">
            Ticket Policy
          </Link>
          , and{" "}
          <Link href="/safety" className="font-semibold text-primary">
            Safety
          </Link>
          .
        </p>
      </div>
    </section>
  );
}
