import Link from "next/link";

import { Button } from "@/components/ui";
import { brand } from "@/lib/brand";

type CtaColumn = {
  eyebrow: string;
  title: string;
  body: string;
  href: string;
  label: string;
  primary?: boolean;
};

function columnsForCategory(categorySlug?: string | null): CtaColumn[] {
  const discover: CtaColumn = {
    eyebrow: "Discover",
    title: `Discover nights on ${brand.name}`,
    body: "Browse events, follow hosts, and keep tickets in one place.",
    href: "/events",
    label: "Explore events",
    primary: true,
  };
  const host: CtaColumn = {
    eyebrow: "Host",
    title: `Host on ${brand.name}`,
    body: "Sell tickets, run check-in, and grow your Legacy.",
    href: "/host/onboarding",
    label: "Start hosting",
  };
  const merch: CtaColumn = {
    eyebrow: "Shop",
    title: "Shop merch",
    body: "Official drops from hosts you already trust.",
    href: "/merch",
    label: "Browse shop",
  };
  const vault: CtaColumn = {
    eyebrow: "Vault",
    title: "Explore Vault",
    body: "Unlock exclusive drops from hosts you follow.",
    href: "/for-fans",
    label: "For fans",
  };
  const safety: CtaColumn = {
    eyebrow: "Safety",
    title: "Stay safe on Pàdéyá",
    body: "Buy on-platform, use signed tickets, and report issues fast.",
    href: "/safety",
    label: "Safety Center",
  };

  switch (categorySlug) {
    case "host-growth":
    case "event-planning":
      return [
        {
          ...host,
          primary: true,
          href: "/host/events/new",
          label: "Create event",
          title: `Host on ${brand.name}`,
        },
        discover,
        merch,
      ];
    case "safety":
      return [safety, discover, host];
    case "fans":
      return [discover, vault, merch];
    case "product":
      return [discover, merch, host];
    case "discovery":
    default:
      return [discover, host, merch];
  }
}

export function BlogRecoveryCtas({
  categorySlug,
}: {
  categorySlug?: string | null;
}) {
  const cols = columnsForCategory(categorySlug);

  return (
    <section
      className="relative overflow-hidden rounded-[var(--radius-xl)] border border-border bg-ink p-6 text-paper shadow-[var(--shadow)] sm:p-8 lg:p-10"
      aria-label="Next steps on Pàdéyá"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_15%_20%,color-mix(in_srgb,var(--primary)_18%,transparent),transparent_52%),linear-gradient(135deg,transparent_40%,color-mix(in_srgb,var(--primary)_8%,transparent))]"
      />
      <div className="relative grid gap-8 sm:grid-cols-3 sm:gap-0">
        {cols.map((col, i) => (
          <div
            key={col.href + col.label}
            className={
              i === 0
                ? "space-y-3 sm:pr-6"
                : "space-y-3 border-t border-paper/10 pt-6 sm:border-l sm:border-t-0 sm:px-6 sm:pt-0"
            }
          >
            <p
              className="text-xs font-bold uppercase tracking-[0.16em]"
              style={{ color: brand.colors.green }}
            >
              {col.eyebrow}
            </p>
            <h2
              className={
                i === 0
                  ? "font-display text-xl font-extrabold tracking-tight sm:text-2xl"
                  : "font-display text-lg font-bold tracking-tight"
              }
            >
              {col.title}
            </h2>
            <p className="text-sm leading-relaxed text-paper/70">{col.body}</p>
            <Link href={col.href}>
              <Button
                size="md"
                variant={col.primary ? "primary" : "outline-dark"}
              >
                {col.label}
              </Button>
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}
