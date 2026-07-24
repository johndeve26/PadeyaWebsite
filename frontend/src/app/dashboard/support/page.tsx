"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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

export default function DashboardSupportPage() {
  const [rows, setRows] = useState<SupportCase[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchMySupportTickets();
        if (active) {
          setRows(items);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load tickets",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Support"
      title="My support tickets"
      description="Track conversations with Pàdéyá support from your personal account."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/support/new">
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

      {rows == null && !error ? <SkeletonLoader lines={4} /> : null}

      {rows && rows.length === 0 && !error ? (
        <EmptyState
          title="No tickets yet"
          description="Open a ticket when something goes wrong with orders, tickets, or your account."
          action={
            <Link href="/dashboard/support/new">
              <Button>Create ticket</Button>
            </Link>
          }
        />
      ) : null}

      {rows && rows.length > 0 ? (
        <ul className="space-y-3">
          {rows.map((ticket) => (
            <li key={ticket.id}>
              <SupportTicketListItem
                ticket={ticket}
                href={`/dashboard/support/${ticket.id}`}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </DashboardShell>
  );
}
