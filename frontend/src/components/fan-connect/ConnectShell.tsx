"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";

const LINKS: { href: string; label: string; exact?: boolean }[] = [
  { href: "/connect", label: "Circle", exact: true },
  { href: "/connect/suggestions", label: "Shared energy" },
  { href: "/connect/events", label: "Same events" },
  { href: "/connect/requests", label: "Requests" },
  { href: "/connect/connections", label: "Connections" },
  { href: "/connect/settings", label: "Privacy" },
];

type Props = {
  title: string;
  description?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
  /** When true, page supplies its own hero (e.g. /connect hub). */
  hideHeader?: boolean;
};

export function ConnectShell({
  title,
  description,
  children,
  actions,
  hideHeader = false,
}: Props) {
  const pathname = usePathname();

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Fan Connect"
      title={title}
      description={
        description ||
        "Meet Explorers going where you’re going — shared public nights, hosts, and scenes."
      }
      actions={actions}
      hideHeader={hideHeader}
    >
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <nav className="flex flex-wrap gap-2" aria-label="Fan Connect">
          {LINKS.map((link) => {
            const active = link.exact
              ? pathname === link.href
              : pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link key={link.href} href={link.href}>
                <Button
                  size="sm"
                  variant={active ? "primary" : "secondary"}
                  className={cn(active && "pointer-events-none")}
                >
                  {link.label}
                </Button>
              </Link>
            );
          })}
        </nav>
        {hideHeader && actions ? (
          <div className="flex flex-wrap gap-2">{actions}</div>
        ) : null}
      </div>
      {children}
    </DashboardShell>
  );
}
