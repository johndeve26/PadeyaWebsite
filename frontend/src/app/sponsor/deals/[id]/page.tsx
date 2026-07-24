"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import { SponsorshipDeliverablesChecklist } from "@/components/sponsor/SponsorshipDeliverablesChecklist";
import { Alert, Button, Container, SectionHeader, StatusBadge } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime, formatNgn } from "@/lib/format";
import {
  acceptSponsorDeal,
  fetchSponsorDeal,
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

export default function SponsorDealDetailPage() {
  const params = useParams();
  const dealId = String(params.id);
  const searchParams = useSearchParams();
  const paymentReturn = searchParams.get("payment") === "return";
  const { active } = useSponsorWorkspace();
  const sponsorId = active?.sponsor_id ?? null;
  const manageable = canManage(
    active ? { is_owner: active.is_owner, role: active.role } : null,
  );

  const [deal, setDeal] = useState<SponsorshipDeal | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!sponsorId) return;
    setDeal(await fetchSponsorDeal(sponsorId, dealId));
  }, [dealId, sponsorId]);

  useEffect(() => {
    if (!sponsorId) return;
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load deal");
      }
    })();
  }, [load, sponsorId]);

  if (!sponsorId) return null;

  return (
    <Container className="space-y-6 py-6">
      <Link href="/sponsor/deals" className="text-sm text-muted hover:text-accent">
        ← All deals
      </Link>
      {paymentReturn ? (
        <Alert tone="info" title="Payment submitted">
          If you completed checkout, status updates after Paystack confirms payment. Refresh
          this page in a moment.
        </Alert>
      ) : null}
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {deal ? (
        <>
          <SectionHeader
            title={deal.title}
            description={deal.host_display_name ?? undefined}
            action={<StatusBadge status={deal.status} />}
          />
          <div className="space-y-4 rounded-lg border border-border p-6">
            <p className="text-muted">{deal.description ?? "No description."}</p>
            <p>
              <span className="font-medium">Amount:</span> {formatNgn(Number(deal.amount))}{" "}
              {deal.currency}
            </p>
            {deal.deliverables?.length ? (
              <ul className="list-disc pl-5 text-sm">
                {deal.deliverables.map((d) => (
                  <li key={d}>{d}</li>
                ))}
              </ul>
            ) : null}
            {deal.invoice ? (
              <div className="rounded-md bg-surface-muted p-4 text-sm">
                <p className="font-medium">Invoice {deal.invoice.invoice_number}</p>
                <p>Status: {deal.invoice.status}</p>
                {deal.invoice.paid_at ? (
                  <p>Paid {formatDateTime(deal.invoice.paid_at)}</p>
                ) : null}
              </div>
            ) : null}
            {manageable && deal.can_accept ? (
              <div className="flex gap-2">
                <Button onClick={() => void acceptSponsorDeal(sponsorId, dealId).then(load)}>
                  Accept proposal
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => void rejectSponsorDeal(sponsorId, dealId).then(load)}
                >
                  Reject
                </Button>
              </div>
            ) : null}
            {manageable && deal.can_pay ? (
              <Button
                onClick={() =>
                  void paySponsorDeal(sponsorId, dealId).then((r) => {
                    window.location.href = r.payment_url;
                  })
                }
              >
                Pay via Paystack
              </Button>
            ) : null}
            {!manageable ? (
              <p className="text-sm text-muted">View-only — ask an admin to accept or pay.</p>
            ) : null}
          </div>
          {(deal.status === "active" || deal.status === "completed") && (
            <section className="space-y-3">
              <h2 className="text-lg font-bold">Deliverables</h2>
              <SponsorshipDeliverablesChecklist
                mode="sponsor"
                dealId={dealId}
                sponsorId={sponsorId}
                canManage={manageable}
              />
            </section>
          )}
        </>
      ) : null}
    </Container>
  );
}
