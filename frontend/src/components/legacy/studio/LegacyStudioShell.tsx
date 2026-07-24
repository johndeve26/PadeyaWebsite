"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button } from "@/components/ui";

const NAV = [
  { href: "/host/legacy", label: "Overview" },
  { href: "/host/legacy/edit", label: "Profile" },
  { href: "/host/legacy/content", label: "Content blocks" },
  { href: "/host/legacy/preview", label: "Preview" },
  { href: "/host/legacy/tier", label: "Tier" },
] as const;

export function LegacyStudioShell({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const pathname = usePathname();

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Legacy Studio"
        title={title}
        description={description}
        actions={actions}
      >
        <nav className="mb-8 flex flex-wrap gap-2 border-b border-border pb-4">
          {NAV.map((item) => {
            const active =
              item.href === "/host/legacy"
                ? pathname === item.href
                : pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link key={item.href} href={item.href}>
                <Button
                  size="sm"
                  variant={active ? "primary" : "ghost"}
                  className={active ? undefined : "text-muted-foreground"}
                >
                  {item.label}
                </Button>
              </Link>
            );
          })}
        </nav>
        {children}
      </DashboardShell>
    </RequireHost>
  );
}
