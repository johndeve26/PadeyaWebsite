import Link from "next/link";

import {
  FALLBACK_FEE_CATEGORIES,
  formatAppearsAt,
  HOST_NET_FORMULA_LINES,
  payerLabel,
  PRICING_FAQ,
  PricingPlatformRelationship,
  PRICING_TIERS,
} from "@/lib/legal/pricing-content";
import { brand } from "@/lib/brand";
import type { PublicPricingFeeRow } from "@/lib/types/pricing";

function SectionTitle({
  id,
  eyebrow,
  title,
  description,
}: {
  id?: string;
  eyebrow?: string;
  title: string;
  description?: string;
}) {
  return (
    <div id={id} className="mx-auto max-w-3xl text-center">
      {eyebrow ? (
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary">
          {eyebrow}
        </p>
      ) : null}
      <h2 className="mt-2 font-display text-2xl font-extrabold text-heading sm:text-3xl">
        {title}
      </h2>
      {description ? (
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          {description}
        </p>
      ) : null}
    </div>
  );
}

export function PricingTier() {
  return (
    <div
      id="audience-tiers"
      className="mx-auto grid max-w-5xl gap-5 lg:grid-cols-3"
      data-testid="pricing-tiers"
    >
      {PRICING_TIERS.map((tier) => (
        <section
          key={tier.name}
          className="rounded-[var(--radius-lg)] border border-border bg-card/80 p-6 shadow-[var(--shadow-soft)] backdrop-blur-sm dark:bg-surface-elevated"
        >
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary">
            {tier.name}
          </p>
          <h3 className="mt-2 font-display text-2xl font-extrabold text-heading">
            {tier.price}
          </h3>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            {tier.blurb}
          </p>
          <ul className="mt-5 space-y-2 text-sm text-foreground">
            {tier.points.map((p) => (
              <li key={p} className="flex gap-2">
                <span className="text-primary" aria-hidden>
                  ✓
                </span>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

export function BuyerFeesSection() {
  return (
    <section
      id="buyer-fees"
      className="mx-auto max-w-5xl rounded-[var(--radius-lg)] border border-border bg-card/80 p-6 dark:bg-surface-elevated sm:p-8"
      data-testid="buyer-fees-section"
    >
      <SectionTitle
        title="Buyer-paid fees"
        description="Clear totals before you pay — no surprise host-commission lines on the buyer receipt."
      />
      <ul className="mx-auto mt-6 grid max-w-3xl gap-3 text-sm text-foreground sm:grid-cols-2">
        {[
          "Buyer platform fee is paid by the buyer.",
          "Buyer fees are shown before payment.",
          "Buyer fees are separate from host deductions.",
          "Payment processing fees may apply depending on configuration.",
          "Final total is shown before you confirm payment.",
          "You pay ticket, merch, and Vault prices listed at checkout.",
        ].map((line) => (
          <li
            key={line}
            className="rounded-[var(--radius-md)] border border-border/70 bg-background/40 px-4 py-3"
          >
            {line}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function HostEarningsSection() {
  return (
    <section
      id="host-earnings"
      className="mx-auto max-w-5xl rounded-[var(--radius-lg)] border border-border bg-card/80 p-6 dark:bg-surface-elevated sm:p-8"
      data-testid="host-earnings-section"
    >
      <SectionTitle
        title="Know what you earn before you sell."
        description="Host-paid fees are deducted from host earnings. Exact deductions appear in Host earnings and finance views."
      />
      <div className="mx-auto mt-6 max-w-xl rounded-[var(--radius-md)] border border-primary/30 bg-primary/5 p-5">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-primary">
          Host net earnings
        </p>
        <p className="mt-3 font-display text-lg font-bold text-heading">=</p>
        <ul className="mt-2 space-y-1 font-mono text-sm text-foreground">
          {HOST_NET_FORMULA_LINES.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>
      <ul className="mx-auto mt-6 max-w-3xl space-y-2 text-sm text-muted-foreground">
        <li>
          Exact deductions are visible in{" "}
          <Link href="/host/earnings" className="font-semibold text-primary">
            Host earnings
          </Link>{" "}
          / finance views.
        </li>
        <li>
          Order fee snapshots preserve the fee terms used at the time of sale.
        </li>
        <li>Host-specific fee overrides may apply — rates may vary by host.</li>
      </ul>
    </section>
  );
}

export function FeeCategoriesSection({
  categories,
  note,
}: {
  categories: PublicPricingFeeRow[];
  note?: string | null;
}) {
  const rows = categories.length > 0 ? categories : FALLBACK_FEE_CATEGORIES;

  return (
    <section id="fee-categories" className="mx-auto max-w-5xl space-y-6">
      <SectionTitle
        eyebrow="Fee categories"
        title="How each fee works"
        description="Configurable by admin. Public rates appear only when meant to be public — otherwise we say may vary."
      />
      {note ? (
        <p className="mx-auto max-w-3xl text-center text-sm text-muted-foreground">
          {note}
        </p>
      ) : null}

      <div
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        data-testid="fee-category-cards"
      >
        {rows.map((row) => (
          <article
            key={row.fee_key}
            className="flex flex-col rounded-[var(--radius-lg)] border border-border bg-card/80 p-5 dark:bg-surface-elevated"
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-display text-lg font-bold text-heading">
                {row.label}
              </h3>
              <span className="shrink-0 rounded-full border border-border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                {payerLabel(row.payer)}
              </span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              {row.public_description}
            </p>
            <dl className="mt-4 space-y-1.5 text-xs text-foreground">
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Rate</dt>
                <dd className="font-semibold tabular-nums">
                  {row.display_rate ?? "May vary"}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Appears</dt>
                <dd className="text-right">{formatAppearsAt(row.appears_at)}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Configurable</dt>
                <dd>{row.configurable ? "Yes" : "No"}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>

      <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-border">
        <table
          className="min-w-[40rem] w-full border-collapse text-left text-sm"
          data-testid="fee-category-table"
        >
          <thead className="bg-surface-muted/80 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-semibold">Category</th>
              <th className="px-4 py-3 font-semibold">Who pays</th>
              <th className="px-4 py-3 font-semibold">How it appears</th>
              <th className="px-4 py-3 font-semibold">Configurable</th>
              <th className="px-4 py-3 font-semibold">Rate / detail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={`table-${row.fee_key}`}
                className="border-t border-border/70 bg-card/40 dark:bg-surface-elevated/60"
              >
                <td className="px-4 py-3 font-medium text-heading">
                  {row.label}
                </td>
                <td className="px-4 py-3">{payerLabel(row.payer)}</td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatAppearsAt(row.appears_at)}
                </td>
                <td className="px-4 py-3">
                  {row.configurable ? "Yes" : "No"}
                </td>
                <td className="px-4 py-3 tabular-nums">
                  {row.display_rate ?? "May vary"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-center text-xs text-muted-foreground">
        View details: buyers at checkout · hosts at{" "}
        <Link href="/host/earnings" className="text-primary">
          /host/earnings
        </Link>{" "}
        · admins in finance tools. Merch formats and flows:{" "}
        <Link href="/merch-guide" className="text-primary">
          /merch-guide
        </Link>
        .
      </p>
    </section>
  );
}

export function HighVolumeSection() {
  return (
    <section
      id="volume"
      className="mx-auto max-w-5xl rounded-[var(--radius-lg)] border border-border bg-card/80 p-6 dark:bg-surface-elevated sm:p-8"
      data-testid="custom-pricing-section"
    >
      <SectionTitle
        title="High-volume & custom pricing"
        description="Festivals, venues, brands, schools, churches, communities, and high-volume hosts may receive custom rates."
      />
      <p className="mx-auto mt-4 max-w-2xl text-center text-sm text-muted-foreground">
        Custom terms are shown in host finance tools when configured. Public
        pricing always says rates may vary — we never list another host’s deal
        here.
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <Link
          href="/support"
          className="inline-flex h-11 items-center justify-center rounded-[var(--radius-md)] bg-primary px-5 text-sm font-semibold text-primary-foreground"
        >
          Contact support
        </Link>
        <Link
          href="/contact"
          className="inline-flex h-11 items-center justify-center rounded-[var(--radius-md)] border border-border bg-background/50 px-5 text-sm font-semibold text-heading"
        >
          Contact sales
        </Link>
      </div>
    </section>
  );
}

export function PricingFaqSection() {
  return (
    <section id="faq" className="mx-auto max-w-3xl space-y-4">
      <SectionTitle
        eyebrow="FAQ"
        title={`Pricing questions for ${brand.name}`}
      />
      <div className="space-y-3" data-testid="pricing-faq">
        {PRICING_FAQ.map((item) => (
          <details
            key={item.q}
            className="group rounded-[var(--radius-lg)] border border-border bg-card/80 px-5 py-4 dark:bg-surface-elevated"
          >
            <summary className="cursor-pointer list-none font-semibold text-heading marker:content-none [&::-webkit-details-marker]:hidden">
              <span className="flex items-center justify-between gap-3">
                {item.q}
                <span className="text-primary transition group-open:rotate-45">
                  +
                </span>
              </span>
            </summary>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              {item.a}
            </p>
          </details>
        ))}
      </div>
    </section>
  );
}

export function PricingBottomCtas() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 rounded-[var(--radius-lg)] border border-primary/25 bg-primary/5 px-6 py-8 text-center">
      <h2 className="font-display text-2xl font-extrabold text-heading">
        Ready for the next night?
      </h2>
      <p className="max-w-lg text-sm text-muted-foreground">
        Explore events as a fan, become a host, or talk to us about custom
        volume pricing.
      </p>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <Link
          href="/events"
          className="inline-flex h-11 items-center justify-center rounded-[var(--radius-md)] bg-primary px-5 text-sm font-semibold text-primary-foreground"
        >
          Explore events
        </Link>
        <Link
          href="/host/onboarding"
          className="inline-flex h-11 items-center justify-center rounded-[var(--radius-md)] border border-border bg-background/60 px-5 text-sm font-semibold text-heading"
        >
          Become a host
        </Link>
        <Link
          href="/support"
          className="inline-flex h-11 items-center justify-center rounded-[var(--radius-md)] border border-transparent px-5 text-sm font-semibold text-primary"
        >
          Contact support
        </Link>
      </div>
    </div>
  );
}

export { PricingPlatformRelationship };
