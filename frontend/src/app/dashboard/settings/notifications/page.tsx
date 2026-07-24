"use client";

import Link from "next/link";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { NotificationPreferencesSections } from "@/components/notifications/NotificationPreferencesSections";
import { Button } from "@/components/ui";

/** Deep-link alias — same email + push controls as Account Settings. */
export default function NotificationSettingsPage() {
  return (
    <DashboardShell
      tone="soft"
      eyebrow="Account"
      title="Notifications"
      description="Email and browser push for Pàdéyá. Purchase confirmations still email after verified payment."
      actions={
        <Link href="/dashboard/settings">
          <Button variant="secondary">Back to settings</Button>
        </Link>
      }
    >
      <NotificationPreferencesSections />
    </DashboardShell>
  );
}
