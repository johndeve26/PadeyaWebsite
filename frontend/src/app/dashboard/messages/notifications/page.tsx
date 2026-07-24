"use client";

import Link from "next/link";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { MessageNotificationsPanel } from "@/components/messaging/MessageNotificationsPanel";
import { Button } from "@/components/ui";

export default function FanMessageNotificationsPage() {
  return (
    <DashboardShell
      tone="soft"
      eyebrow="Inbox"
      title="Message notifications"
      description="Safe summaries only — full message bodies stay in the conversation."
      actions={
        <Link href="/dashboard/messages">
          <Button variant="secondary">Back to messages</Button>
        </Link>
      }
    >
      <MessageNotificationsPanel />
    </DashboardShell>
  );
}
