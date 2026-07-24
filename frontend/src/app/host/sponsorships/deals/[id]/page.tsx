"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { SponsorshipDeliverablesChecklist } from "@/components/sponsor/SponsorshipDeliverablesChecklist";
import { Alert, Button, Container, SectionHeader, StatusBadge } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import {
  cancelHostSponsorshipDeal,
  fetchHostSponsorshipDeal,
  sendHostSponsorshipDeal,
  type SponsorshipDeal,
} from "@/lib/sponsor-deals-api";

export default function HostSponsorshipDealDetailPage() {
  const params = useParams();
  const dealId = String(params.id);
  const [deal, setDeal] = useState<SponsorshipDeal | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setDeal(await fetchHostSponsorshipDeal(dealId));
  }, [dealId]);

  useEffect(() => {
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load deal");
      }
    })();
  }, [load]);

  return (
    <Container className="space-y-6 py-6">
      <Link href="/host/sponsorships/deals" className="text-sm text-muted hover:text-accent">
        ← All deals
      </Link>
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {deal ? (
        <>
          <SectionHeader
            title={deal.title}
            description={deal.sponsor_display_name ?? undefined}
            action={<StatusBadge status={deal.status} />}
          />
          <div className="space-y-3 rounded-lg border border-border p-6">
            <p>{deal.description}</p>
            <p>{formatNgn(Number(deal.amount))} {deal.currency}</p>
            {deal.invoice ? (
              <p className="text-sm text-muted">
                Invoice {deal.invoice.invoice_number} — {deal.invoice.status}
              </p>
            ) : null}
            {deal.can_edit && deal.status === "draft" ? (
              <Button onClick={() => void sendHostSponsorshipDeal(dealId).then(load)}>
                Send to sponsor
              </Button>
            ) : null}
            {deal.status === "draft" || deal.status === "proposed" ? (
              <Button
                variant="secondary"
                onClick={() => void cancelHostSponsorshipDeal(dealId).then(load)}
              >
                Cancel proposal
              </Button>
            ) : null}
          </div>
          {(deal.status === "active" || deal.status === "completed") && (
            <section className="space-y-3">
              <h2 className="text-lg font-bold">Deliverables</h2>
              <SponsorshipDeliverablesChecklist mode="host" dealId={dealId} canManage />
            </section>
          )}
        </>
      ) : null}
    </Container>
  );
}
