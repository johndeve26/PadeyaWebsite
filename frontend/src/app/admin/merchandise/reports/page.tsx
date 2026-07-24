"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  ConfirmAction,
  DataTable,
  EmptyState,
  FilterBar,
  Select,
  SkeletonLoader,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime, formatNgn } from "@/lib/format";
import {
  fetchAdminMerchReports,
  resolveMerchReport,
  updateMerchReport,
} from "@/lib/merch-api";
import type { MerchReport } from "@/lib/types/merch";

const OPEN_STATUSES = new Set(["open", "reviewing"]);

export default function AdminMerchandiseReportsPage() {
  const [items, setItems] = useState<MerchReport[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [adminNotes, setAdminNotes] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("open");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const rows = await fetchAdminMerchReports({
      status: statusFilter === "all" ? undefined : statusFilter,
      limit: 200,
    });
    setItems(rows);
    setAdminNotes((prev) => {
      const next = { ...prev };
      for (const row of rows) {
        if (next[row.id] === undefined) {
          next[row.id] = row.admin_notes ?? "";
        }
      }
      return next;
    });
  }, [statusFilter]);

  useEffect(() => {
    let active = true;
    void (async () => {
      setLoading(true);
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load reports");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function onMarkReviewing(id: string) {
    setError(null);
    setBusyId(id);
    try {
      await updateMerchReport(id, {
        status: "reviewing",
        admin_notes: adminNotes[id]?.trim() || null,
      });
      setNote("Report marked as reviewing");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    } finally {
      setBusyId(null);
    }
  }

  async function onSaveAdminNotes(id: string) {
    setError(null);
    setBusyId(id);
    try {
      await updateMerchReport(id, {
        admin_notes: adminNotes[id]?.trim() || null,
      });
      setNote("Admin notes saved");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save notes");
    } finally {
      setBusyId(null);
    }
  }

  async function onResolve(
    id: string,
    resolution: "resolved" | "dismissed",
    moderateAction?: "hide" | "archive" | "clear",
  ) {
    const itemNote = notes[id]?.trim() ?? "";
    if (
      (moderateAction === "hide" || moderateAction === "archive") &&
      !itemNote
    ) {
      setError("Reason is required when hiding or archiving a product");
      return;
    }
    setError(null);
    setBusyId(id);
    try {
      await resolveMerchReport(id, {
        resolution,
        note: itemNote || undefined,
        admin_notes: adminNotes[id]?.trim() || null,
        moderate_action: moderateAction,
      });
      setNotes((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      setNote(
        resolution === "dismissed"
          ? "Report dismissed"
          : moderateAction
            ? `Report resolved and product ${moderateAction}d`
            : "Report resolved",
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Resolve failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Merchandise reports"
      description="Review reported merch listings. Statuses: open, reviewing, resolved, dismissed. Actions are audited."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/merchandise">
            <Button variant="secondary">Products</Button>
          </Link>
          <Link href="/admin/merchandise/orders">
            <Button variant="secondary">Orders</Button>
          </Link>
          <Link href="/admin">
            <Button variant="ghost">Admin home</Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Action failed">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Updated">
          {note}
        </Alert>
      ) : null}

      <FilterBar
        trailing={
          <span className="text-sm text-muted-foreground">
            {items.length} report{items.length === 1 ? "" : "s"}
          </span>
        }
      >
        <Select
          label="Report status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="open">Open</option>
          <option value="reviewing">Reviewing</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
          <option value="all">All</option>
        </Select>
      </FilterBar>

      {loading && !error ? <SkeletonLoader lines={4} /> : null}

      {!loading && items.length === 0 && !error ? (
        <EmptyState
          title="No reports"
          description="No merchandise reports match this filter."
        />
      ) : !loading ? (
        <DataTable
          rows={items}
          rowKey={(item) => item.id}
          emptyTitle="No matching reports"
          emptyDescription="Try another status filter."
          columns={[
            {
              key: "product",
              header: "Product snapshot",
              primary: true,
              cell: (item) => {
                const snap = item.product_snapshot;
                const image = snap?.image_url;
                return (
                  <div className="flex gap-3">
                    <div className="h-14 w-14 shrink-0 overflow-hidden rounded-[var(--radius-sm)] bg-surface-muted">
                      {image ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={image}
                          alt=""
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <span className="flex h-full items-center justify-center text-[10px] font-bold uppercase text-muted-foreground">
                          Merch
                        </span>
                      )}
                    </div>
                    <div className="min-w-0 space-y-1">
                      <p className="font-semibold text-foreground">
                        {snap?.name ?? item.product_name ?? "Product"}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {item.event_title ?? "Event"} · {item.host_name ?? "Host"}
                      </p>
                      {snap ? (
                        <p className="text-xs text-muted-foreground">
                          {formatNgn(Number(snap.base_price))} · {snap.status} ·{" "}
                          {snap.moderation_status}
                        </p>
                      ) : null}
                      <Link
                        href={`/admin/merchandise/${item.product_id}`}
                        className="text-xs font-semibold text-foreground underline-offset-2 hover:underline"
                      >
                        View product
                      </Link>
                    </div>
                  </div>
                );
              },
            },
            {
              key: "report",
              header: "Report",
              cell: (item) => (
                <div className="space-y-1 text-sm">
                  <p className="font-medium text-foreground">{item.reason}</p>
                  {item.details ? (
                    <p className="whitespace-pre-wrap text-muted-foreground">
                      {item.details}
                    </p>
                  ) : null}
                  <p className="text-xs text-muted-foreground">
                    Reporter: {item.reporter_name ?? "user"} ·{" "}
                    {formatDateTime(item.created_at)}
                  </p>
                </div>
              ),
            },
            {
              key: "status",
              header: "Status",
              cell: (item) => <StatusBadge status={item.status} />,
            },
            {
              key: "admin_notes",
              header: "Admin notes",
              cell: (item) =>
                OPEN_STATUSES.has(item.status) ? (
                  <div className="space-y-2">
                    <Textarea
                      label="Admin notes"
                      rows={2}
                      value={adminNotes[item.id] ?? ""}
                      onChange={(e) =>
                        setAdminNotes((prev) => ({
                          ...prev,
                          [item.id]: e.target.value,
                        }))
                      }
                      placeholder="Internal notes for moderators"
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={busyId === item.id}
                      onClick={() => void onSaveAdminNotes(item.id)}
                    >
                      Save notes
                    </Button>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {item.admin_notes ?? "—"}
                  </p>
                ),
            },
            {
              key: "resolution",
              header: "Resolution note",
              cell: (item) =>
                OPEN_STATUSES.has(item.status) ? (
                  <Textarea
                    label="Resolution note"
                    rows={2}
                    value={notes[item.id] ?? ""}
                    onChange={(e) =>
                      setNotes((prev) => ({ ...prev, [item.id]: e.target.value }))
                    }
                    placeholder="Required when hiding or archiving"
                  />
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {item.resolution_note ?? "—"}
                    {item.resolved_by_name
                      ? ` · ${item.resolved_by_name}`
                      : ""}
                  </p>
                ),
            },
            {
              key: "actions",
              header: "Actions",
              cell: (item) => {
                if (!OPEN_STATUSES.has(item.status)) {
                  return (
                    <span className="text-sm text-muted-foreground">Closed</span>
                  );
                }
                const busy = busyId === item.id;
                return (
                  <div className="flex flex-wrap justify-end gap-1.5 md:justify-start">
                    {item.status === "open" ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busy}
                        onClick={() => void onMarkReviewing(item.id)}
                      >
                        Mark reviewing
                      </Button>
                    ) : null}
                    <Button
                      size="sm"
                      disabled={busy}
                      onClick={() => void onResolve(item.id, "resolved")}
                    >
                      Resolve
                    </Button>
                    <ConfirmAction
                      label="Resolve + hide"
                      title="Hide listing and resolve?"
                      description={`Hide “${item.product_name ?? "product"}” and close this report.`}
                      confirmLabel="Hide and resolve"
                      tone="danger"
                      disabled={busy}
                      busy={busy}
                      onConfirm={() => onResolve(item.id, "resolved", "hide")}
                    />
                    <ConfirmAction
                      label="Resolve + archive"
                      title="Archive listing and resolve?"
                      description={`Archive “${item.product_name ?? "product"}” and close this report.`}
                      confirmLabel="Archive and resolve"
                      tone="danger"
                      disabled={busy}
                      busy={busy}
                      onConfirm={() => onResolve(item.id, "resolved", "archive")}
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={busy}
                      onClick={() => void onResolve(item.id, "dismissed")}
                    >
                      Dismiss
                    </Button>
                  </div>
                );
              },
            },
          ]}
        />
      ) : null}
    </DashboardShell>
  );
}
