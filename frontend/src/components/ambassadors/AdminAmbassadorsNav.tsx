"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

const LINKS: { href: string; label: string; exact?: boolean }[] = [
  { href: "/admin/ambassadors", label: "Overview", exact: true },
  { href: "/admin/ambassadors/campaigns", label: "Campaigns" },
  { href: "/admin/ambassadors/conversions", label: "Conversions" },
  { href: "/admin/ambassadors/fraud", label: "Fraud flags" },
  { href: "/admin/ambassadors/payouts", label: "Payouts" },
  { href: "/admin/ambassadors/reports", label: "Reports" },
];

export function AdminAmbassadorsNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Admin Ambassadors"
      className="mb-6 flex flex-wrap gap-1 border-b border-border pb-px"
    >
      {LINKS.map((link) => {
        const active = link.exact
          ? pathname === link.href
          : pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "rounded-t-md px-3 py-2 text-sm font-semibold transition-colors",
              active
                ? "border-b-2 border-[var(--brand-green)] text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
