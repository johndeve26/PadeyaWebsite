"use client";

import Link from "next/link";

import { RequireHost } from "@/components/hosts/RequireHost";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { SupportTicketForm } from "@/components/support/SupportTicketForm";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button, Card } from "@/components/ui";

function HostNewSupportInner() {
  const { active } = useHostWorkspace();

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Host workspace"
      title="New support ticket"
      description="We'll attach this ticket to your active host workspace when available."
      actions={
        <Link href="/host/support">
          <Button variant="secondary">Host tickets</Button>
        </Link>
      }
    >
      <Card className="relative max-w-2xl space-y-4 p-5 sm:p-6">
        <SupportTicketForm
          requesterContext="host"
          relatedHostId={active?.host_id ?? null}
          successHrefForTicket={(id) => `/host/support/${id}`}
        />
      </Card>
    </DashboardShell>
  );
}

export default function HostNewSupportTicketPage() {
  return (
    <RequireHost>
      <HostNewSupportInner />
    </RequireHost>
  );
}
