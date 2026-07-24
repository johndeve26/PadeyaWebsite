"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { BuyerTicketsDashboard } from "@/components/tickets/BuyerTicketsDashboard";
import { TicketTransferHistoryPanel } from "@/components/tickets/TicketTransferHistoryPanel";
import {
  Alert,
  Button,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { fetchMyTickets } from "@/lib/commerce-api";
import {
  cacheTicketListForOffline,
  readCachedTicketList,
} from "@/lib/pwa/offline-ticket-cache";
import { useOnlineStatus } from "@/lib/pwa/use-online-status";
import type { Ticket } from "@/lib/types/commerce";

export default function MyTicketsPage() {
  const online = useOnlineStatus();
  const [tickets, setTickets] = useState<Ticket[]>(() => readCachedTicketList());
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(() => readCachedTicketList().length > 0);
  const [fromCache, setFromCache] = useState(
    () => readCachedTicketList().length > 0,
  );
  const [ticketListKey, setTicketListKey] = useState(0);

  function refreshTickets() {
    setTicketListKey((k) => k + 1);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchMyTickets();
        if (!active) return;
        cacheTicketListForOffline(items);
        setTickets(items);
        setFromCache(false);
        setError(null);
        setLoaded(true);
      } catch (err) {
        if (!active) return;
        setLoaded(true);
        if (readCachedTicketList().length) {
          setError(null);
        } else {
          setError(err instanceof Error ? err.message : "Failed to load tickets");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [ticketListKey]);

  return (
    <DashboardShell
      tone="soft"
      compact
      title="My tickets"
      description="Open your QR codes, download passes, and manage event entry."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/orders">
            <Button variant="secondary">View orders</Button>
          </Link>
          <Link href="/events">
            <Button variant="primary">Browse events</Button>
          </Link>
        </div>
      }
    >
      {!online || fromCache ? (
        <Alert
          tone={!online ? "warning" : "info"}
          title={!online ? "Offline" : "Refreshing"}
        >
          {!online
            ? "You’re offline — showing cached tickets when available. Door scanners still validate online."
            : "Refreshing tickets from the server…"}
        </Alert>
      ) : null}
      {error ? (
        <Alert tone="danger" title="Could not load tickets">
          {error}
        </Alert>
      ) : null}
      {!loaded ? <SkeletonLoader lines={5} /> : null}
      {loaded && tickets.length === 0 && !error ? (
        <EmptyState
          title="No active tickets"
          description="When you buy tickets for upcoming events, your QR passes will appear here. Pending transfers you sent are listed below."
          action={
            <Link href="/events">
              <Button size="lg">Browse events</Button>
            </Link>
          }
        />
      ) : null}
      {loaded && tickets.length > 0 ? (
        <BuyerTicketsDashboard tickets={tickets} />
      ) : null}
      {loaded ? (
        <TicketTransferHistoryPanel onTicketsChanged={refreshTickets} />
      ) : null}
    </DashboardShell>
  );
}
