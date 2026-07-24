"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  Alert,
  DataTable,
  SectionHeader,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { formatDateTime } from "@/lib/format";
import {
  fetchAdminSponsors,
  type SponsorAdminRow,
} from "@/lib/sponsor-profiles-api";

export default function AdminSponsorsPage() {
  const { user } = useAuth();
  const canView = userHasPermission(user, "admin.sponsors.view");
  const [rows, setRows] = useState<SponsorAdminRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchAdminSponsors();
    setRows(data);
  }, []);

  useEffect(() => {
    if (!canView) return;
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load sponsors");
      }
    })();
  }, [canView, load]);

  if (!canView) {
    return (
      <Alert tone="danger" title="Access denied">
        You need admin.sponsors.view to manage sponsor profiles.
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Platform"
        title="Sponsor profiles"
        description="Verify, restrict, or review sponsor workspace identities. Does not auto-approve messaging or host matching."
      />
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {rows === null ? (
        <SkeletonLoader />
      ) : (
        <DataTable
          columns={[
            {
              key: "name",
              header: "Sponsor",
              primary: true,
              cell: (r) => (
                <Link
                  href={`/admin/sponsors/${r.id}`}
                  className="font-semibold text-accent underline-offset-2 hover:underline"
                >
                  {r.display_name}
                </Link>
              ),
            },
            {
              key: "verification",
              header: "Verification",
              cell: (r) => (
                <StatusBadge tone="neutral">{r.verification_status}</StatusBadge>
              ),
            },
            {
              key: "status",
              header: "Status",
              cell: (r) => <StatusBadge tone="neutral">{r.status}</StatusBadge>,
            },
            {
              key: "created",
              header: "Created",
              cell: (r) => formatDateTime(r.created_at),
            },
          ]}
          rows={rows}
          rowKey={(r) => r.id}
          emptyTitle="No sponsor profiles"
        />
      )}
    </div>
  );
}
