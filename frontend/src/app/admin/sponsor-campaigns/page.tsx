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
import { formatDateTime } from "@/lib/format";
import {
  adminApproveSponsorCampaign,
  adminRejectSponsorCampaign,
  fetchAdminSponsorCampaigns,
} from "@/lib/sponsor-campaigns-api";

export default function AdminSponsorCampaignsPage() {
  const { user } = useAuth();
  const canView = userHasPermission(user, "admin.sponsor_campaigns.view");
  const canModerate = userHasPermission(user, "admin.sponsor_campaigns.moderate");
  const [rows, setRows] = useState<
    Awaited<ReturnType<typeof fetchAdminSponsorCampaigns>> | null
  >(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRows(await fetchAdminSponsorCampaigns());
  }, []);

  useEffect(() => {
    if (!canView) return;
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load campaigns");
      }
    })();
  }, [canView, load]);

  if (!canView) {
    return (
      <Alert tone="danger" title="Access denied">
        You need admin.sponsor_campaigns.view.
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Admin"
        title="Sponsor campaigns"
        description="Moderate public case-study campaigns on Pàdéyá. Private sponsor budgets and goals stay workspace-only."
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
              key: "name",
              header: "Campaign",
              cell: (r) => r.name,
              primary: true,
            },
            { key: "sponsor", header: "Sponsor", cell: (r) => r.sponsor_name },
            { key: "status", header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
            {
              key: "mod",
              header: "Moderation",
              cell: (r) => r.moderation_status,
            },
            {
              key: "created",
              header: "Created",
              cell: (r) => formatDateTime(r.created_at),
            },
            {
              key: "actions",
              header: "",
              cell: (r) =>
                canModerate && r.moderation_status === "pending" ? (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() =>
                        void (async () => {
                          await adminApproveSponsorCampaign(r.id);
                          await load();
                        })()
                      }
                    >
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        void (async () => {
                          const reason = window.prompt("Rejection reason");
                          if (!reason) return;
                          await adminRejectSponsorCampaign(r.id, reason);
                          await load();
                        })()
                      }
                    >
                      Reject
                    </Button>
                  </div>
                ) : null,
            },
          ]}
          rows={rows}
          rowKey={(r) => r.id}
          emptyTitle="No sponsor campaigns."
        />
      )}
      <Link href="/admin/sponsors" className="text-sm text-accent underline">
        Back to sponsors
      </Link>
    </div>
  );
}
