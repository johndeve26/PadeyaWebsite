"use client";

import Link from "next/link";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { MessageSettingsForm } from "@/components/messaging/MessageSettingsForm";
import { Button } from "@/components/ui";

export default function HostMessageSettingsPage() {
  return (
    <DashboardShell
      tone="soft"
      eyebrow="Operate"
      title="Message settings"
      description="Host inbox preferences, event inquiries, auto-reply, and blocked fans. Lagos Comedy Hub has auto-reply on in the demo seed."
      actions={
        <Link href="/host/messages">
          <Button variant="secondary">Back to messages</Button>
        </Link>
      }
    >
      <MessageSettingsForm mode="host" />
    </DashboardShell>
  );
}
