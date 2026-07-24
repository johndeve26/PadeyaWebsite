"use client";

import Link from "next/link";

import { AccountNotificationsPanel } from "@/components/notifications/AccountNotificationsPanel";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button } from "@/components/ui";

export default function HostNotificationsPage() {
  return (
    <DashboardShell
      tone="soft"
      operationalHeader
      eyebrow="Host"
      title="Alerts"
      description="Account alerts while you stay in this host workspace."
      actions={
        <Link href="/dashboard/settings/notifications">
          <Button size="sm" variant="secondary">
            Preferences
          </Button>
        </Link>
      }
    >
      <AccountNotificationsPanel listFallbackHref="/host/notifications" />
    </DashboardShell>
  );
}
