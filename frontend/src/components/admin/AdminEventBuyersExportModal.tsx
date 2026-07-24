"use client";

import { useMemo, useState } from "react";

import { Alert, Button, Input, Modal, Select } from "@/components/ui";
import {
  exportAdminEventBuyers,
  type AdminBuyerFilters,
  type AdminExportFormat,
  type AdminExportMode,
} from "@/lib/admin-event-buyers-api";

const MODE_OPTIONS: { value: AdminExportMode; label: string }[] = [
  { value: "public_summary", label: "Public summary" },
  { value: "operations", label: "Operations" },
  { value: "finance", label: "Finance" },
];

function filterSummary(filters: AdminBuyerFilters): string[] {
  const lines: string[] = [];
  if (filters.q) lines.push(`Search: ${filters.q}`);
  if (filters.ticket_status || filters.purchase_status) {
    lines.push(
      `Purchase status: ${filters.purchase_status || filters.ticket_status}`,
    );
  }
  if (filters.payment_status) lines.push(`Payment: ${filters.payment_status}`);
  if (filters.refund_status) lines.push(`Refund: ${filters.refund_status}`);
  if (filters.checked_in) lines.push(`Checked in: ${filters.checked_in}`);
  if (filters.ticket_type) lines.push(`Ticket type: ${filters.ticket_type}`);
  if (filters.promo_code) lines.push(`Promo: ${filters.promo_code}`);
  if (filters.ambassador_code) {
    lines.push(`Ambassador: ${filters.ambassador_code}`);
  }
  if (filters.purchased_from || filters.purchased_to) {
    lines.push(
      `Purchased: ${filters.purchased_from || "…"} → ${filters.purchased_to || "…"}`,
    );
  }
  return lines;
}

export function AdminEventBuyersExportModal({
  open,
  onClose,
  eventId,
  filters,
  onExported,
}: {
  open: boolean;
  onClose: () => void;
  eventId: string;
  filters: AdminBuyerFilters;
  onExported?: () => void;
}) {
  const [format, setFormat] = useState<AdminExportFormat>("csv");
  const [mode, setMode] = useState<AdminExportMode>("operations");
  const [reason, setReason] = useState("");
  const [includePrivate, setIncludePrivate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeFilters = useMemo(() => filterSummary(filters), [filters]);
  const reasonRequired =
    mode === "finance" ||
    (mode === "operations" && includePrivate);

  async function confirm() {
    setError(null);
    if (format === "xlsx") {
      setError("XLSX export is not available. Choose CSV.");
      return;
    }
    if (reasonRequired && !reason.trim()) {
      setError(
        "A reason is required for finance exports and when including private contact.",
      );
      return;
    }
    setBusy(true);
    try {
      await exportAdminEventBuyers(eventId, {
        ...filters,
        format,
        mode,
        reason: reason.trim() || undefined,
        include_private_contact: includePrivate,
      });
      onExported?.();
      onClose();
      setReason("");
      setIncludePrivate(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Export event buyers"
      description="Downloads respect the filters currently applied to this list."
      footer={
        <>
          <Button variant="secondary" size="sm" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button size="sm" onClick={() => void confirm()} disabled={busy}>
            {busy ? "Exporting…" : "Confirm export"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error ? (
          <Alert tone="danger" title="Export blocked">
            {error}
          </Alert>
        ) : null}

        <Alert tone="warning" title="Audited export">
          Exports are audited. Do not download private contact or finance data
          unless needed for event operations or support.
        </Alert>

        <Select
          label="Format"
          value={format}
          onChange={(e) => setFormat(e.target.value as AdminExportFormat)}
        >
          <option value="csv">CSV</option>
          <option value="json">JSON</option>
          <option value="xlsx" disabled>
            XLSX (unavailable)
          </option>
        </Select>

        <Select
          label="Mode"
          value={mode}
          onChange={(e) => setMode(e.target.value as AdminExportMode)}
        >
          {MODE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>

        {(mode === "operations" || mode === "finance") && (
          <label className="flex items-start gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              className="mt-1"
              checked={includePrivate}
              onChange={(e) => setIncludePrivate(e.target.checked)}
            />
            <span>
              Include private contact (email/phone) — requires{" "}
              <code className="text-xs">admin.events.export_private_contact</code>{" "}
              and a reason
            </span>
          </label>
        )}

        <div>
          <p className="mb-1 text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
            Active filters
          </p>
          {activeFilters.length === 0 ? (
            <p className="text-sm text-muted-foreground">None — all matching buyers</p>
          ) : (
            <ul className="list-inside list-disc text-sm text-foreground">
              {activeFilters.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
        </div>

        <Input
          label={reasonRequired ? "Reason (required)" : "Reason (optional)"}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Why is this export needed?"
        />
      </div>
    </Modal>
  );
}
