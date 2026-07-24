"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Badge,
  Button,
  Card,
  StatCard,
  WorkspaceNavGrid,
} from "@/components/ui";
import { fetchStaffRefunds } from "@/lib/finance-api";

const supportNav = [
  {
    href: "/support/cases",
    title: "Support cases",
    description: "Assign, reply, escalate, resolve, and archive product support cases.",
    meta: "Primary",
  },
  {
    href: "/support/refunds",
    title: "Refund queue",
    description: "Triage cases, add notes, and escalate — support cannot mark payouts paid.",
    meta: "Finance-safe",
  },
  {
    href: "/events",
    title: "Browse events",
    description: "Check public listings when helping attendees with order context.",
    meta: "Reference",
  },
  {
    href: "/admin/support/ai-summary",
    title: "AI case summary",
    description: "Draft themes from open refunds — suggestions only, no approvals.",
    meta: "Tools",
  },
  {
    href: "/admin",
    title: "Admin tools",
    description: "Shared ops surfaces when your role permits access.",
    meta: "Shared",
  },
];

export default function SupportPage() {
  const { user } = useAuth();
  const [openRefunds, setOpenRefunds] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const rows = await fetchStaffRefunds();
        if (!active) return;
        setOpenRefunds(
          rows.filter((r) => ["requested", "under_review"].includes(r.status))
            .length,
        );
      } catch {
        // Inbox stats are optional.
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Support"
      title="Agent inbox"
      description="Help attendees and hosts on Pàdéyá. Escalate finance-sensitive refunds — never mark payouts paid."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/support/cases">
            <Button variant="secondary" size="lg">
              Support cases
            </Button>
          </Link>
          <Link href="/support/refunds">
            <Button size="lg">Open refund queue</Button>
          </Link>
        </div>
      }
    >
      {openRefunds != null ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard
            title="Open cases"
            value={openRefunds}
            hint="Requested or under review"
            href="/support/refunds"
          />
          <StatCard
            title="Escalation path"
            value="Finance"
            hint="Support cannot mark payouts paid"
          />
        </div>
      ) : null}

      <WorkspaceNavGrid items={supportNav} />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-2">
          <p className="text-sm font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Agent
          </p>
          <h2 className="text-xl font-extrabold text-foreground">
            {user?.full_name ?? "—"}
          </h2>
          <div className="flex flex-wrap gap-2">
            {(user?.roles ?? ["support"]).map((role) => (
              <Badge key={role} tone="accent">
                {role}
              </Badge>
            ))}
          </div>
        </Card>
        <Card className="space-y-4 border-l-4 border-l-accent">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.12em] text-muted-foreground">
              Guidelines
            </p>
            <h3 className="mt-1 text-lg font-extrabold text-foreground">
              Before you act
            </h3>
          </div>
          <ul className="space-y-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
            <li className="flex gap-2">
              <span className="font-bold text-foreground">1.</span>
              Escalate finance-sensitive refunds — do not mark paid.
            </li>
            <li className="flex gap-2">
              <span className="font-bold text-foreground">2.</span>
              Never share demo credentials outside local environments.
            </li>
            <li className="flex gap-2">
              <span className="font-bold text-foreground">3.</span>
              Use audit-friendly notes on every case update.
            </li>
          </ul>
          <Link href="/support/refunds">
            <Button>Triage refund queue</Button>
          </Link>
        </Card>
      </div>
    </DashboardShell>
  );
}
