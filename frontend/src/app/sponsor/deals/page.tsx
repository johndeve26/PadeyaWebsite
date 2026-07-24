"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
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
  acceptSponsorDeal,
  fetchSponsorDeals,
  paySponsorDeal,
  rejectSponsorDeal,
  type SponsorshipDeal,
} from "@/lib/sponsor-deals-api";

function canManage(active: { is_owner: boolean; role: string } | null): boolean {
  if (!active) return false;
  return (
    active.is_owner ||
    active.role === "admin" ||
    active.role === "campaign_manager"
  );
}

export default function SponsorDealsPage() {
  const { active } = useSponsorWorkspace();
  const sponsorId = active?.sponsor_id ?? null;
  const manageable = canManage(
    active ? { is_owner: active.is_owner, role: active.role } : null,
  );

  const [items, setItems] = useState<SponsorshipDeal[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!sponsorId) return;
    setItems(await fetchSponsorDeals(sponsorId));
  }, [sponsorId]);

  useEffect(() => {
    if (!sponsorId) return;
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load deals");
      }
    })();
  }, [load, sponsorId]);

  if (!sponsorId) return null;

  return (
    <Container className="space-y-6 py-6">
      <SectionHeader
        eyebrow="Manage"
        title="Sponsorship deals"
        description="Review host proposals, accept packages, and pay invoices on Pàdéyá. Placement activates only after verified payment."
      />
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {items.length === 0 ? (
        <EmptyState
          title="No deals yet"
          description="When a host sends a proposal from your inquiry, it will appear here."
        />
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {items.map((row) => (
            <li key={row.id} className="flex flex-wrap items-center gap-4 p-4">
              <div className="min-w-0 flex-1">
                <Link
                  href={`/sponsor/deals/${row.id}`}
                  className="font-semibold text-foreground hover:text-accent"
                >
                  {row.title}
                </Link>
                <p className="text-sm text-muted">
                  {row.host_display_name ?? "Host"} · {formatNgn(Number(row.amount))} ·{" "}
                  {formatDateTime(row.updated_at)}
                </p>
              </div>
              <StatusBadge status={row.status} />
              {manageable && row.can_accept ? (
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() =>
                      void acceptSponsorDeal(sponsorId, row.id).then(load)
                    }
                  >
                    Accept
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      void rejectSponsorDeal(sponsorId, row.id).then(load)
                    }
                  >
                    Reject
                  </Button>
                </div>
              ) : null}
              {manageable && row.can_pay ? (
                <Button
                  size="sm"
                  onClick={() =>
                    void paySponsorDeal(sponsorId, row.id).then((r) => {
                      window.location.href = r.payment_url;
                    })
                  }
                >
                  Pay invoice
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </Container>
  );
}
