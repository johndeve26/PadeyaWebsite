"use client";

import Link from "next/link";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { MessageNotificationsPanel } from "@/components/messaging/MessageNotificationsPanel";
import { Button } from "@/components/ui";

export default function HostMessageNotificationsPage() {
  return (
    <DashboardShell
      tone="soft"
      eyebrow="Operate"
      title="Message notifications"
      description="Safe summaries only — full message bodies stay in the conversation."
      actions={
        <Link href="/host/messages">
          <Button variant="secondary">Back to messages</Button>
        </Link>
      }
    >
      <MessageNotificationsPanel />
    </DashboardShell>
  );
}
