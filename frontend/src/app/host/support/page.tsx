"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { SupportTicketListItem } from "@/components/support/SupportTicketListItem";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMySupportTickets } from "@/lib/support-api";
import type { SupportCase } from "@/lib/types/support";

function HostSupportInner() {
  const { active } = useHostWorkspace();
  const [rows, setRows] = useState<SupportCase[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const items = await fetchMySupportTickets();
        if (alive) {
          setRows(items);
          setError(null);
        }
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load tickets",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const hostTickets = useMemo(() => {
    if (!rows) return null;
    const hostId = active?.host_id;
    return rows.filter((t) => {
      if (t.requester_context === "host") return true;
      if (hostId && t.related_host_id === hostId) return true;
      return false;
    });
  }, [rows, active?.host_id]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Host workspace"
      title="Support"
      description="Escalate platform, payout, and event issues to Pàdéyá support."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/host/support/new">
            <Button>New ticket</Button>
          </Link>
          <Link href="/support">
            <Button variant="secondary">Support Center</Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Could not load tickets">
          {error}
        </Alert>
      ) : null}

      {hostTickets == null && !error ? <SkeletonLoader lines={4} /> : null}

      {hostTickets && hostTickets.length === 0 && !error ? (
        <EmptyState
          title="No host tickets yet"
          description="Open a ticket for billing, payouts, or platform issues blocking your events."
          action={
            <Link href="/host/support/new">
              <Button>Create ticket</Button>
            </Link>
          }
        />
      ) : null}

      {hostTickets && hostTickets.length > 0 ? (
        <ul className="space-y-3">
          {hostTickets.map((ticket) => (
            <li key={ticket.id}>
              <SupportTicketListItem
                ticket={ticket}
                href={`/host/support/${ticket.id}`}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </DashboardShell>
  );
}

export default function HostSupportPage() {
  return (
    <RequireHost>
      <HostSupportInner />
    </RequireHost>
  );
}
