"use client";

import Link from "next/link";

import { cn } from "@/lib/cn";

const TYPES = [
  {
    title: "Standalone merch",
    body: "Host shop products you can buy anytime — not tied to a single night.",
    href: "/merch?type=standalone#catalog",
    badge: "Host shops",
  },
  {
    title: "Event add-ons",
    body: "Bundle merch with tickets at checkout or on the event page.",
    href: "/merch?type=event_addon#catalog",
    badge: "Add-on",
  },
  {
    title: "Post-event drops",
    body: "Limited releases after the night for fans who attended or bought in.",
    href: "/merch/drops",
    badge: "Drop",
  },
  {
    title: "Vault exclusives",
    body: "Premium merch unlocked through a host’s Vault membership.",
    href: "/merch/vault",
    badge: "Vault",
  },
  {
    title: "Bundles",
    body: "Ticket + merch combos and multi-item packs from hosts.",
    href: "/merch?type=bundle#catalog",
    badge: "Bundle",
  },
] as const;

export function MerchTypeCards({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5",
        className,
      )}
    >
      {TYPES.map((item) => (
        <Link
          key={item.title}
          href={item.href}
          className="group flex flex-col gap-2 rounded-[var(--radius-lg)] border border-border bg-card p-4 transition-colors hover:border-primary/40 dark:bg-surface-elevated"
        >
          <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-primary">
            {item.badge}
          </span>
          <h3 className="text-base font-extrabold tracking-tight text-heading group-hover:text-primary-text">
            {item.title}
          </h3>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {item.body}
          </p>
        </Link>
      ))}
    </div>
  );
}
