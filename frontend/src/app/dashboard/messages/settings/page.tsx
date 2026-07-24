"use client";

import Link from "next/link";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { MessageSettingsForm } from "@/components/messaging/MessageSettingsForm";
import { Button } from "@/components/ui";

export default function FanMessageSettingsPage() {
  return (
    <DashboardShell
      tone="soft"
      eyebrow="Inbox"
      title="Message settings"
      description="Control who can message you on Pàdéyá. Public messaging is off for demo fans by default."
      actions={
        <Link href="/dashboard/messages">
          <Button variant="secondary">Back to messages</Button>
        </Link>
      }
    >
      <MessageSettingsForm mode="fan" />
    </DashboardShell>
  );
}
