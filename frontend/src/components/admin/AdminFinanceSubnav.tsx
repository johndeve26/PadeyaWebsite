"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button, Card } from "@/components/ui";

const FINANCE_NAV = [
  { href: "/admin/finance", label: "Overview" },
  { href: "/admin/finance/fees", label: "Fees" },
  { href: "/admin/finance/host-overrides", label: "Host overrides" },
  { href: "/admin/finance/earnings", label: "Earnings" },
  { href: "/admin/finance/platform-revenue", label: "Platform revenue" },
  { href: "/admin/payouts", label: "Payouts" },
] as const;

export function AdminFinanceSubnav() {
  const pathname = usePathname();

  return (
    <Card className="flex flex-wrap gap-2 p-3">
      {FINANCE_NAV.map(({ href, label }) => {
        const active =
          pathname === href ||
          (href !== "/admin/finance" && pathname.startsWith(`${href}/`));
        return (
          <Link key={href} href={href}>
            <Button size="sm" variant={active ? "dark" : "ghost"}>
              {label}
            </Button>
          </Link>
        );
      })}
    </Card>
  );
}
