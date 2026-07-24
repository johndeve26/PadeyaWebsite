"use client";

import { useEffect, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import { Alert, Container, DataTable, SectionHeader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  fetchMySponsorInquiries,
  type SponsorInquiryRow,
} from "@/lib/sponsor-profiles-api";

export default function SponsorInquiriesPage() {
  const { active } = useSponsorWorkspace();
  const [rows, setRows] = useState<SponsorInquiryRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    void (async () => {
      try {
        setRows(await fetchMySponsorInquiries(active.sponsor_id));
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load inquiries");
      }
    })();
  }, [active]);

  return (
    <Container className="space-y-6 py-6">
      <SectionHeader
        eyebrow="Manage"
        title="Inquiries"
        description="Track sponsorship inquiries you sent to hosts. Hosts respond on their timeline — sponsors cannot message fans directly."
      />
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      <DataTable
        columns={[
          {
            key: "host",
            header: "Host",
            cell: (r) => r.host_display_name ?? "—",
            primary: true,
          },
          { key: "slot", header: "Slot", cell: (r) => r.slot_title ?? "—" },
          { key: "status", header: "Status", cell: (r) => r.status },
          {
            key: "sent",
            header: "Sent",
            cell: (r) => formatDateTime(r.created_at),
          },
        ]}
        rows={rows ?? []}
        rowKey={(r) => r.id}
        emptyTitle={rows === null ? "Loading…" : "No inquiries yet."}
      />
    </Container>
  );
}
