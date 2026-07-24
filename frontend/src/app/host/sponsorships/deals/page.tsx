"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Button,
  Container,
  EmptyState,
  SectionHeader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime, formatNgn } from "@/lib/format";
import {
  cancelHostSponsorshipDeal,
  fetchHostSponsorshipDeals,
  fetchHostSponsorshipRevenue,
  sendHostSponsorshipDeal,
  type HostSponsorshipRevenueReport,
  type SponsorshipDeal,
} from "@/lib/sponsor-deals-api";

export default function HostSponsorshipDealsPage() {
  const [items, setItems] = useState<SponsorshipDeal[]>([]);
  const [revenue, setRevenue] = useState<HostSponsorshipRevenueReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setItems(await fetchHostSponsorshipDeals());
    setRevenue(await fetchHostSponsorshipRevenue());
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load deals");
      }
    })();
  }, [load]);

  return (
    <Container className="space-y-6 py-6">
      <SectionHeader
        eyebrow="Grow"
        title="Sponsorship deals"
        description="Send proposals to sponsors, track invoices, and see revenue after verified payment on Pàdéyá."
        action={
          <Link href="/host/sponsorships">
            <Button variant="secondary">Manage slots</Button>
          </Link>
        }
      />
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {revenue ? (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm text-muted">Pending revenue</p>
            <p className="text-xl font-semibold">
              {revenue.revenue_pending_ngn
                ? formatNgn(Number(revenue.revenue_pending_ngn))
                : "—"}
            </p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm text-muted">Paid revenue</p>
            <p className="text-xl font-semibold">
              {revenue.revenue_paid_ngn
                ? formatNgn(Number(revenue.revenue_paid_ngn))
                : "—"}
            </p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm text-muted">Pending deliverables</p>
            <p className="text-xl font-semibold">{revenue.pending_deliverables}</p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm text-muted">Overdue deliverables</p>
            <p className="text-xl font-semibold">{revenue.overdue_deliverables}</p>
          </div>
        </div>
      ) : null}
      {items.length === 0 ? (
        <EmptyState
          title="No deals yet"
          description="Create a proposal from a sponsor inquiry to start the deal lifecycle."
        />
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {items.map((row) => (
            <li key={row.id} className="flex flex-wrap items-center gap-4 p-4">
              <div className="min-w-0 flex-1">
                <Link
                  href={`/host/sponsorships/deals/${row.id}`}
                  className="font-semibold hover:text-accent"
                >
                  {row.title}
                </Link>
                <p className="text-sm text-muted">
                  {row.sponsor_display_name ?? "Sponsor"} · {formatNgn(Number(row.amount))}
                </p>
              </div>
              <StatusBadge status={row.status} />
              {row.status === "draft" ? (
                <Button size="sm" onClick={() => void sendHostSponsorshipDeal(row.id).then(load)}>
                  Send proposal
                </Button>
              ) : null}
              {row.status === "draft" || row.status === "proposed" ? (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => void cancelHostSponsorshipDeal(row.id).then(load)}
                >
                  Cancel
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </Container>
  );
}
