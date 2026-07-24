"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

const LINKS: { href: string; label: string; exact?: boolean }[] = [
  { href: "/admin/notifications", label: "Overview", exact: true },
  { href: "/admin/notifications/settings", label: "Settings" },
  { href: "/admin/notifications/campaigns", label: "Campaigns" },
  { href: "/admin/notifications/templates", label: "Templates" },
];

export function AdminNotificationsNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Admin notifications"
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
