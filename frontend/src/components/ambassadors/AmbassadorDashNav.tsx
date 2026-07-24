"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

const links = [
  { href: "/dashboard/ambassador", label: "Overview" },
  { href: "/dashboard/ambassador/events", label: "Campaigns" },
  { href: "/dashboard/ambassador/links", label: "Links & QR" },
  { href: "/dashboard/ambassador/earnings", label: "Earnings" },
  { href: "/dashboard/ambassador/leaderboard", label: "Leaderboard" },
  { href: "/dashboard/ambassador/payouts", label: "Payouts" },
];

export function AmbassadorDashNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Ambassador dashboard"
      className="flex flex-wrap gap-2 border-b border-border pb-3"
    >
      {links.map((link) => {
        const active =
          link.href === "/dashboard/ambassador"
            ? pathname === link.href
            : pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "rounded-[var(--radius-sm)] px-3 py-1.5 text-sm font-semibold transition",
              active
                ? "bg-ink text-paper"
                : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
