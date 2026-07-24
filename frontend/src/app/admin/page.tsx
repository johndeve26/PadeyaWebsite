"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { AdminAISummaryPanel } from "@/components/admin/AdminAISummaryPanel";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Badge,
  Button,
  Card,
  SectionHeader,
  StatCard,
  WorkspaceNavGrid,
  type WorkspaceNavItem,
} from "@/components/ui";
import { fetchPendingEvents } from "@/lib/events-api";
import { fetchAdminPayouts, fetchStaffRefunds } from "@/lib/finance-api";

const adminSections: { eyebrow: string; items: WorkspaceNavItem[] }[] = [
  {
    eyebrow: "Ops",
    items: [
      {
        href: "/admin/events/review",
        title: "Event review queue",
        description: "Approve or reject pending listings before they go live.",
        meta: "Priority",
      },
      {
        href: "/admin/events",
        title: "Events",
        description: "Browse and moderate published and pending event inventory.",
        meta: "Listings",
      },
      {
        href: "/admin/featured-placements",
        title: "Featured Placement Slots",
        description:
          "Primary and Secondary Spotlights for homepage, events, location, and category contexts.",
        meta: "Editorial",
      },
      {
        href: "/admin/orders",
        title: "Orders",
        description: "Order lookup and buyer purchase context.",
        meta: "Commerce",
      },
      {
        href: "/admin/tickets",
        title: "Tickets",
        description: "Issued tickets, transfers, and check-in references.",
        meta: "Commerce",
      },
    ],
  },
  {
    eyebrow: "Finance",
    items: [
      {
        href: "/admin/finance",
        title: "Finance overview",
        description: "Fees, earnings, payouts, and settlement entry points.",
        meta: "Finance",
      },
      {
        href: "/admin/finance/fees",
        title: "Fees",
        description: "Platform commissions, service fees, and processing fees.",
        meta: "Finance",
      },
      {
        href: "/admin/finance/host-overrides",
        title: "Host fee overrides",
        description: "Per-host commission and fee exceptions.",
        meta: "Finance",
      },
      {
        href: "/admin/refunds",
        title: "Refunds",
        description: "Finance-sensitive cases with audited decisions.",
        meta: "Finance",
      },
      {
        href: "/admin/payouts",
        title: "Payouts",
        description: "Host payout review and mark-paid controls with evidence.",
        meta: "Finance",
      },
      {
        href: "/admin/payments",
        title: "Payments",
        description: "Payment records and gateway reconciliation.",
        meta: "Finance",
      },
      {
        href: "/admin/ledger",
        title: "Ledger",
        description: "Platform ledger entries and balance movements.",
        meta: "Finance",
      },
    ],
  },
  {
    eyebrow: "Moderation",
    items: [
      {
        href: "/admin/hosts",
        title: "Hosts",
        description: "Approve or reject host verification and open Legacy tools.",
        meta: "Trust",
      },
      {
        href: "/admin/support",
        title: "Support",
        description: "Cases, refund triage, and AI summaries for operators.",
        meta: "Ops",
      },
      {
        href: "/admin/reviews",
        title: "Reviews",
        description: "Moderate verified reviews and reports.",
        meta: "Trust",
      },
      {
        href: "/admin/message-reports",
        title: "Message reports",
        description: "Review reported in-app conversations (no private contact data).",
        meta: "Trust",
      },
      {
        href: "/admin/sponsorships",
        title: "Sponsorships",
        description: "Flag, approve, or remove marketplace packages.",
        meta: "Brands",
      },
      {
        href: "/admin/vault",
        title: "Vault",
        description: "Moderate exclusive content listings.",
        meta: "Content",
      },
      {
        href: "/admin/merchandise",
        title: "Merchandise",
        description:
          "Moderate event merch listings, orders/fulfillment issues, and reports (no payment secrets).",
        meta: "Commerce",
      },
      {
        href: "/admin/ambassadors",
        title: "Ambassadors",
        description:
          "Platform campaigns, blocks, conversion reversals, and reward status.",
        meta: "Growth",
      },
      {
        href: "/admin/memories",
        title: "Memories",
        description: "Post-event galleries and host thank-you content.",
        meta: "Content",
      },
    ],
  },
  {
    eyebrow: "Content & ops",
    items: [
      {
        href: "/admin/cms",
        title: "CMS",
        description: "Blog posts, FAQs, and homepage banners.",
        meta: "Content",
      },
      {
        href: "/admin/categories",
        title: "Categories",
        description: "Event category catalog — activate or deactivate.",
        meta: "Catalog",
      },
      {
        href: "/admin/emails",
        title: "Email outbox",
        description: "Queued transactional emails and delivery status.",
        meta: "Ops",
      },
      {
        href: "/admin/email/settings",
        title: "Email settings",
        description:
          "Choose provider, configure encrypted SMTP, test delivery — no .env redeploy.",
        meta: "Ops",
      },
      {
        href: "/admin/push/settings",
        title: "Push settings",
        description:
          "Enable browser push with encrypted VAPID keys — no .env redeploy.",
        meta: "Ops",
      },
      {
        href: "/admin/audit-logs",
        title: "Audit logs",
        description: "Immutable trail of sensitive platform actions.",
        meta: "Security",
      },
      {
        href: "/admin/users",
        title: "Users",
        description: "Browse, search, deactivate, or restore accounts (hard delete blocked).",
        meta: "Security",
      },
      {
        href: "/admin/fans",
        title: "Fan Passports",
        description:
          "Moderate Fan Passport Directory visibility — hide or restore public Passports.",
        meta: "Community",
      },
      {
        href: "/admin/fan-connect",
        title: "Fan Connect",
        description:
          "Opt-in fan↔fan Connect overview, reports, and blocks — no private attendee data.",
        meta: "Community",
      },
    ],
  },
  {
    eyebrow: "Insights",
    items: [
      {
        href: "/admin/analytics",
        title: "Analytics",
        description: "Platform-level performance dashboards.",
        meta: "Insights",
      },
      {
        href: "/admin/ai",
        title: "Pàdéyá AI",
        description: "Admin controls, usage, feature toggles, and draft playground.",
        meta: "AI",
      },
      {
        href: "/admin/legacy",
        title: "Legacy",
        description: "Host reputation and tier oversight.",
        meta: "Reputation",
      },
    ],
  },
];

type QueueCounts = {
  pendingEvents: number;
  openRefunds: number;
  pendingPayouts: number;
};

export default function AdminPage() {
  const { user } = useAuth();
  const roles = user?.roles ?? [];
  const permissionCount = user?.permissions?.length ?? 0;
  const [queues, setQueues] = useState<QueueCounts | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [pending, refunds, payouts] = await Promise.all([
          fetchPendingEvents(),
          fetchStaffRefunds(),
          fetchAdminPayouts(),
        ]);
        if (!active) return;
        setQueues({
          pendingEvents: pending.length,
          openRefunds: refunds.filter((r) =>
            ["requested", "under_review"].includes(r.status),
          ).length,
          pendingPayouts: payouts.filter((p) =>
            ["requested", "under_review", "approved"].includes(p.status),
          ).length,
        });
      } catch {
        // Queue counts are optional — overview still works without them.
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Platform administration"
      description="Operations, approvals, moderation, and finance oversight for Pàdéyá — with audit trails."
      actions={
        <Link href="/admin/events/review">
          <Button size="lg">Review queue</Button>
        </Link>
      }
    >
      {queues ? (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            title="Pending events"
            value={queues.pendingEvents}
            hint="Awaiting review"
            href="/admin/events/review"
          />
          <StatCard
            title="Open refunds"
            value={queues.openRefunds}
            hint="Requested or under review"
            href="/admin/refunds"
          />
          <StatCard
            title="Payout queue"
            value={queues.pendingPayouts}
            hint="Needs finance action"
            href="/admin/payouts"
          />
        </div>
      ) : null}

      <AdminAISummaryPanel
        feature="admin.operations.daily_summary"
        title="Daily operations AI summary"
        generateLabel="Generate daily summary"
        links={[
          { href: "/admin/support", label: "Support" },
          { href: "/admin/analytics", label: "Analytics" },
          { href: "/admin/reviews", label: "Reports" },
          { href: "/admin/events/review", label: "Event review" },
        ]}
      />

      <div className="space-y-10">
        {adminSections.map((section) => (
          <section key={section.eyebrow} className="space-y-4">
            <SectionHeader eyebrow={section.eyebrow} title={`${section.eyebrow} workspace`} />
            <WorkspaceNavGrid items={section.items} className="xl:grid-cols-2" />
          </section>
        ))}
      </div>

      <Card className="space-y-3">
        <p className="text-sm font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Signed in
        </p>
        <h2 className="text-xl font-extrabold text-foreground break-all">
          {user?.email}
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          {roles.length > 0 ? (
            roles.map((role) => (
              <Badge key={role} tone="accent">
                {role}
              </Badge>
            ))
          ) : (
            <Badge tone="neutral">No roles</Badge>
          )}
          <Badge tone="outline">
            {permissionCount} permission{permissionCount === 1 ? "" : "s"}
          </Badge>
        </div>
      </Card>
    </DashboardShell>
  );
}
