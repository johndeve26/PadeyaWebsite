"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button, Card } from "@/components/ui";

const ANALYTICS_NAV = [
  { href: "/admin/analytics", label: "Overview" },
  { href: "/admin/analytics/revenue", label: "Revenue" },
  { href: "/admin/analytics/events", label: "Events" },
  { href: "/admin/analytics/hosts", label: "Hosts" },
  { href: "/admin/analytics/support", label: "Support" },
] as const;

export function AdminAnalyticsSubnav() {
  const pathname = usePathname();

  return (
    <Card className="flex flex-wrap gap-2 p-3">
      {ANALYTICS_NAV.map(({ href, label }) => (
        <Link key={href} href={href}>
          <Button size="sm" variant={pathname === href ? "dark" : "ghost"}>
            {label}
          </Button>
        </Link>
      ))}
    </Card>
  );
}
