"use client";

import Link from "next/link";

import { AdminFinanceSubnav } from "@/components/admin/AdminFinanceSubnav";
import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Card, PageToolbar, SectionHeader } from "@/components/ui";
import { userHasPermission } from "@/lib/auth/permissions";
import { FEE_HELP_COPY } from "@/lib/types/fees";

const LINKS = [
  {
    href: "/admin/finance/fees",
    title: "Platform fees",
    description:
      "Configure ticket, merch, Vault, service, and processing fee schedules.",
  },
  {
    href: "/admin/finance/host-overrides",
    title: "Host fee overrides",
    description:
      "Special rates per host (e.g. 3% vs default 5% ticket commission).",
  },
  {
    href: "/admin/finance/earnings",
    title: "Earnings",
    description: "Host gross, deductions, and net after Pàdéyá fees.",
  },
  {
    href: "/admin/finance/platform-revenue",
    title: "Platform revenue",
    description:
      "Append-only ledger for payment volume, commissions, refunds, and payouts.",
  },
  {
    href: "/admin/payouts",
    title: "Payouts",
    description: "Review host payouts and mark paid with evidence.",
  },
  {
    href: "/admin/ledger",
    title: "Ledger",
    description: "Append-only balance movements.",
  },
  {
    href: "/admin/refunds",
    title: "Refunds",
    description: "Finance-sensitive refund decisions.",
  },
];

export default function AdminFinanceOverviewPage() {
  const { user } = useAuth();
  const canView = userHasPermission(
    user,
    "admin.finance.view_fees",
    "admin.finance.manage_fees",
    "admin.full_access",
    "payments.view",
    "payouts.review",
  );

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Finance"
      description="Configure how Pàdéyá makes money, review earnings, and manage payouts."
    >
      <div className="space-y-6">
        <AdminFinanceSubnav />
        <PageToolbar>
          <Link href="/admin/finance/fees">
            <Button size="sm" variant="ghost">
              Fees
            </Button>
          </Link>
          <Link href="/admin/finance/host-overrides">
            <Button size="sm" variant="ghost">
              Overrides
            </Button>
          </Link>
          <Link href="/admin/payouts">
            <Button size="sm" variant="ghost">
              Payouts
            </Button>
          </Link>
        </PageToolbar>

        {!canView ? (
          <Alert tone="warning">
            You need finance permissions to manage fees. Support roles cannot
            edit fee schedules.
          </Alert>
        ) : null}

        <Card className="space-y-3 p-5">
          <SectionHeader title="How fees work" />
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
            {FEE_HELP_COPY.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2">
          {LINKS.map((item) => (
            <Link key={item.href} href={item.href} className="block">
              <Card className="h-full space-y-2 p-5 transition hover:border-primary">
                <h2 className="text-lg font-semibold text-heading">
                  {item.title}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {item.description}
                </p>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </DashboardShell>
  );
}
