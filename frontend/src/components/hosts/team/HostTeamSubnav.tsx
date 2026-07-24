"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

const LINKS: { href: string; label: string; exact?: boolean }[] = [
  { href: "/host/team", label: "Overview", exact: true },
  { href: "/host/team/members", label: "Members" },
  { href: "/host/team/invites", label: "Invites" },
  { href: "/host/team/audit-log", label: "Audit log" },
];

export function HostTeamSubnav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Host team sections"
      className="mb-8 flex flex-wrap gap-1 border-b border-border pb-px"
    >
      {LINKS.map((link) => {
        const staticSection =
          pathname.startsWith("/host/team/members") ||
          pathname.startsWith("/host/team/invites") ||
          pathname.startsWith("/host/team/audit-log");
        const memberDetail =
          /^\/host\/team\/[^/]+$/.test(pathname) && pathname !== "/host/team";
        let active = link.exact
          ? pathname === link.href
          : pathname === link.href || pathname.startsWith(`${link.href}/`);
        if (link.href === "/host/team/members" && memberDetail && !staticSection) {
          active = true;
        }
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
