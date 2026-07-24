"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  Alert,
  Button,
  DataTable,
  SectionHeader,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { formatDateTime, formatNgn } from "@/lib/format";
import {
  adminCancelSponsorshipDeal,
  fetchAdminSponsorshipDeals,
  type SponsorshipDeal,
} from "@/lib/sponsor-deals-api";

export default function AdminSponsorshipDealsPage() {
  const { user } = useAuth();
  const canView = userHasPermission(user, "admin.sponsorship_deals.view");
  const canManage = userHasPermission(user, "admin.sponsorship_deals.manage");
  const [rows, setRows] = useState<SponsorshipDeal[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRows(await fetchAdminSponsorshipDeals());
  }, []);

  useEffect(() => {
    if (!canView) return;
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load deals");
      }
    })();
  }, [canView, load]);

  if (!canView) {
    return (
      <Alert tone="danger" title="Access denied">
        You need admin.sponsorship_deals.view.
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Admin"
        title="Sponsorship deals"
        description="Audit deal and invoice status on Pàdéyá. Payment provider payloads are never shown here."
      />
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {rows === null ? (
        <SkeletonLoader rows={4} />
      ) : (
        <DataTable
          columns={[
            {
              key: "title",
              header: "Deal",
              cell: (r) => (
                <Link href={`/admin/sponsorship-deals/${r.id}`} className="font-medium hover:text-accent">
                  {r.title}
                </Link>
              ),
              primary: true,
            },
            { key: "sponsor", header: "Sponsor", cell: (r) => r.sponsor_display_name ?? "—" },
            { key: "host", header: "Host", cell: (r) => r.host_display_name ?? "—" },
            {
              key: "amount",
              header: "Amount",
              cell: (r) => formatNgn(Number(r.amount)),
            },
            { key: "status", header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
            {
              key: "inv",
              header: "Invoice",
              cell: (r) => r.invoice?.status ?? "—",
            },
            {
              key: "updated",
              header: "Updated",
              cell: (r) => formatDateTime(r.updated_at),
            },
            {
              key: "actions",
              header: "",
              cell: (r) =>
                canManage && !["cancelled", "completed", "active"].includes(r.status) ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => void adminCancelSponsorshipDeal(r.id).then(load)}
                  >
                    Cancel
                  </Button>
                ) : null,
            },
          ]}
          rows={rows}
          rowKey={(r) => r.id}
        />
      )}
    </div>
  );
}
