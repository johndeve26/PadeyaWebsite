"use client";

import Link from "next/link";

import { AdminAISummaryPanel } from "@/components/admin/AdminAISummaryPanel";
import { AdminFanConnectReports } from "@/components/fan-connect/AdminFanConnectReports";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button } from "@/components/ui";

export default function AdminFanConnectReportsPage() {
  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Fan Connect"
      title="Reports"
      description="Review Fan Connect reports and safe connection context. Emails, phones, orders, and payments are never shown. Moderate fan↔fan chat only via Message reports when a thread was reported there."
      actions={
        <>
          <Link href="/admin/fan-connect">
            <Button variant="secondary">Overview</Button>
          </Link>
          <Link href="/admin/fan-connect/blocks">
            <Button variant="secondary">Blocks</Button>
          </Link>
          <Link href="/admin/message-reports">
            <Button variant="secondary">Message reports</Button>
          </Link>
        </>
      }
    >
      <div className="space-y-6">
        <AdminAISummaryPanel
          feature="admin.reports.summary"
          title="Reports AI summary"
          generateLabel="Summarize reports"
          links={[
            { href: "/admin/reviews", label: "Review reports" },
            { href: "/admin/message-reports", label: "Message reports" },
          ]}
        />
        <AdminFanConnectReports />
      </div>
    </DashboardShell>
  );
}
