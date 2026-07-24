"use client";

import Link from "next/link";

import { AccountNotificationsPanel } from "@/components/notifications/AccountNotificationsPanel";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button } from "@/components/ui";

export default function DashboardNotificationsPage() {
  return (
    <DashboardShell
      tone="soft"
      eyebrow="Account"
      title="Notifications"
      description="Your Pàdéyá alert inbox. Works even when browser push is off."
      actions={
        <Link href="/dashboard/settings/notifications">
          <Button size="sm" variant="secondary">
            Preferences
          </Button>
        </Link>
      }
    >
      <AccountNotificationsPanel />
    </DashboardShell>
  );
}
