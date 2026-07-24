"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { SponsorshipDeliverablesChecklist } from "@/components/sponsor/SponsorshipDeliverablesChecklist";
import { Alert, Button, SectionHeader, StatusBadge } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { formatNgn } from "@/lib/format";
import {
  adminCancelSponsorshipDeal,
  adminVoidSponsorshipInvoice,
  fetchAdminSponsorshipDeal,
  type SponsorshipDeal,
} from "@/lib/sponsor-deals-api";

export default function AdminSponsorshipDealDetailPage() {
  const params = useParams();
  const dealId = String(params.id);
  const { user } = useAuth();
  const canView = userHasPermission(user, "admin.sponsorship_deals.view");
  const canManage = userHasPermission(user, "admin.sponsorship_deals.manage");
  const canFinance = userHasPermission(user, "admin.sponsorship_deals.finance");
  const [deal, setDeal] = useState<SponsorshipDeal | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setDeal(await fetchAdminSponsorshipDeal(dealId));
  }, [dealId]);

  useEffect(() => {
    if (!canView) return;
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load deal");
      }
    })();
  }, [canView, load, dealId]);

  if (!canView) {
    return (
      <Alert tone="danger" title="Access denied">
        You need admin.sponsorship_deals.view.
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <Link href="/admin/sponsorship-deals" className="text-sm text-muted hover:text-accent">
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
            action={<StatusBadge status={deal.status} />}
          />
          <div className="space-y-2 rounded-lg border border-border p-6">
            <p>Sponsor: {deal.sponsor_display_name}</p>
            <p>Host: {deal.host_display_name}</p>
            <p>{formatNgn(Number(deal.amount))}</p>
            {deal.invoice ? (
              <div className="mt-4 text-sm">
                <p>
                  Invoice {deal.invoice.invoice_number} — {deal.invoice.status}
                </p>
                {canFinance &&
                deal.invoice.status !== "paid" &&
                deal.invoice.status !== "void" ? (
                  <Button
                    className="mt-2"
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      void adminVoidSponsorshipInvoice(deal.invoice!.id).then(load)
                    }
                  >
                    Void invoice
                  </Button>
                ) : null}
              </div>
            ) : null}
            {canManage && !["cancelled", "completed"].includes(deal.status) ? (
              <Button
                variant="secondary"
                onClick={() => void adminCancelSponsorshipDeal(dealId).then(load)}
              >
                Cancel deal
              </Button>
            ) : null}
          </div>
          <section className="space-y-3">
            <h2 className="text-lg font-bold">Deliverables</h2>
            <SponsorshipDeliverablesChecklist mode="admin" dealId={dealId} />
          </section>
        </>
      ) : null}
    </div>
  );
}
