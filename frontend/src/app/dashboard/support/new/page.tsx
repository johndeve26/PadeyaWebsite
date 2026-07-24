"use client";

import Link from "next/link";

import { SupportTicketForm } from "@/components/support/SupportTicketForm";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button, Card } from "@/components/ui";

export default function DashboardNewSupportTicketPage() {
  return (
    <DashboardShell
      tone="soft"
      eyebrow="Support"
      title="New support ticket"
      description="We'll reply in this conversation. Include order or event details when you can."
      actions={
        <Link href="/dashboard/support">
          <Button variant="secondary">My tickets</Button>
        </Link>
      }
    >
      <Card className="relative max-w-2xl space-y-4 p-5 sm:p-6">
        <SupportTicketForm
          requesterContext="fan"
          successHrefForTicket={(id) => `/dashboard/support/${id}`}
        />
      </Card>
    </DashboardShell>
  );
}
