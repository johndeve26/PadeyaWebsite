"use client";

import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Button,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  approveSponsorDeliverable,
  fetchHostDeliverables,
  fetchSponsorDeliverables,
  fetchAdminDeliverables,
  hostPatchDeliverable,
  hostSubmitDeliverable,
  rejectSponsorDeliverable,
  type SponsorshipDeliverable,
} from "@/lib/sponsor-deals-api";

type Mode = "host" | "sponsor" | "admin";

export function SponsorshipDeliverablesChecklist({
  mode,
  dealId,
  sponsorId,
  canManage,
}: {
  mode: Mode;
  dealId: string;
  sponsorId?: string;
  canManage?: boolean;
}) {
  const [items, setItems] = useState<SponsorshipDeliverable[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [proofUrl, setProofUrl] = useState<Record<string, string>>({});
  const [rejectReason, setRejectReason] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    if (mode === "host") {
      setItems(await fetchHostDeliverables(dealId));
    } else if (mode === "sponsor" && sponsorId) {
      setItems(await fetchSponsorDeliverables(sponsorId, dealId));
    } else if (mode === "admin") {
      setItems(await fetchAdminDeliverables(dealId));
    }
  }, [dealId, mode, sponsorId]);

  useEffect(() => {
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load deliverables");
      }
    })();
  }, [load]);

  if (error) {
    return (
      <Alert tone="danger" title="Deliverables">
        {error}
      </Alert>
    );
  }

  if (items.length === 0) {
    return (
      <p className="text-sm text-muted">
        Deliverables appear when the deal is active and payment is confirmed.
      </p>
    );
  }

  return (
    <ul className="space-y-4">
      {items.map((row) => (
        <li
          key={row.id}
          className="rounded-lg border border-border p-4 space-y-2"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold">{row.title}</span>
            <StatusBadge status={row.status} />
            <span className="text-xs text-muted capitalize">
              {row.deliverable_type.replace(/_/g, " ")}
            </span>
          </div>
          {row.description ? (
            <p className="text-sm text-muted">{row.description}</p>
          ) : null}
          {row.due_at ? (
            <p className="text-xs text-muted">Due {formatDateTime(row.due_at)}</p>
          ) : null}
          {row.proof_notes ? (
            <p className="text-sm">Notes: {row.proof_notes}</p>
          ) : null}
          {row.proof_url ? (
            <p className="text-sm">
              Proof:{" "}
              <a
                href={row.proof_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent underline"
              >
                View link
              </a>
            </p>
          ) : null}
          {row.rejection_reason ? (
            <p className="text-sm text-destructive">Revision: {row.rejection_reason}</p>
          ) : null}

          {mode === "host" && canManage && row.can_host_edit ? (
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  void hostPatchDeliverable(dealId, row.id, {
                    status: "in_progress",
                  }).then(load)
                }
              >
                Mark in progress
              </Button>
            </div>
          ) : null}

          {mode === "host" && canManage && row.can_host_submit ? (
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
              <input
                className="flex-1 rounded-md border border-border px-3 py-2 text-sm"
                placeholder="Proof URL (https://…)"
                value={proofUrl[row.id] ?? ""}
                onChange={(e) =>
                  setProofUrl((p) => ({ ...p, [row.id]: e.target.value }))
                }
              />
              <Button
                size="sm"
                onClick={() => {
                  const url = proofUrl[row.id]?.trim();
                  if (!url) return;
                  void hostSubmitDeliverable(dealId, row.id, {
                    proof_url: url,
                  }).then(load);
                }}
              >
                Submit proof
              </Button>
            </div>
          ) : null}

          {mode === "sponsor" && canManage && row.can_sponsor_review ? (
            <div className="flex flex-col gap-2">
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() =>
                    void approveSponsorDeliverable(
                      sponsorId!,
                      dealId,
                      row.id,
                    ).then(load)
                  }
                >
                  Approve
                </Button>
              </div>
              <input
                className="rounded-md border border-border px-3 py-2 text-sm"
                placeholder="Revision notes"
                value={rejectReason[row.id] ?? ""}
                onChange={(e) =>
                  setRejectReason((p) => ({ ...p, [row.id]: e.target.value }))
                }
              />
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  const reason = rejectReason[row.id]?.trim();
                  if (!reason) return;
                  void rejectSponsorDeliverable(sponsorId!, dealId, row.id, {
                    rejection_reason: reason,
                  }).then(load);
                }}
              >
                Request revision
              </Button>
            </div>
          ) : null}

          {mode === "sponsor" && !canManage ? (
            <p className="text-xs text-muted">View-only</p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
