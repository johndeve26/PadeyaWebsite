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
  Input,
  Select,
  SkeletonLoader,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDate, formatNgn } from "@/lib/format";
import {
  deactivateUnsafeMerchProduct,
  fetchAdminMerchProducts,
  moderateMerchProduct,
} from "@/lib/merch-api";
import type { MerchAdminProduct, MerchModerateAction } from "@/lib/types/merch";

const MOD_STATUSES = ["clear", "flagged", "hidden", "removed"] as const;
const PRODUCT_STATUSES = ["draft", "active", "paused", "archived"] as const;
const REASON_REQUIRED = new Set<MerchModerateAction>([
  "hide",
  "remove",
  "archive",
  "restore",
]);

export default function AdminMerchandisePage() {
  const [items, setItems] = useState<MerchAdminProduct[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [modFilter, setModFilter] = useState("all");
  const [sponsorFilter, setSponsorFilter] = useState("all");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => window.clearTimeout(t);
  }, [search]);

  const load = useCallback(async () => {
    const rows = await fetchAdminMerchProducts({
      status: statusFilter === "all" ? undefined : statusFilter,
      moderation_status: modFilter === "all" ? undefined : modFilter,
      q: debouncedSearch || undefined,
      is_sponsor_branded:
        sponsorFilter === "all" ? undefined : sponsorFilter === "yes",
      limit: 200,
    });
    setItems(rows);
  }, [statusFilter, modFilter, sponsorFilter, debouncedSearch]);

  useEffect(() => {
    let active = true;
    void (async () => {
      setLoading(true);
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load merchandise");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function onModerate(id: string, action: MerchModerateAction) {
    const itemNote = notes[id]?.trim() ?? "";
    if (REASON_REQUIRED.has(action) && !itemNote) {
      setError("Moderation reason is required for hide, archive, and restore");
      return;
    }
    setError(null);
    setBusyId(id);
    try {
      await moderateMerchProduct(id, action, itemNote || undefined);
      setNotes((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      const labels: Record<MerchModerateAction, string> = {
        flag: "flagged",
        clear: "cleared",
        hide: "hidden",
        remove: "archived",
        archive: "archived",
        restore: "restored",
      };
      setNote(`Merchandise ${labels[action]}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Moderation failed");
    } finally {
      setBusyId(null);
    }
  }

  async function onDeactivateUnsafe(id: string) {
    const itemNote = notes[id]?.trim() ?? "";
    setError(null);
    setBusyId(id);
    try {
      await deactivateUnsafeMerchProduct(id, itemNote || undefined);
      setNote("Merchandise deactivated for unsafe host/event");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Deactivate failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Merchandise"
      description="View and moderate event merch listings. Hidden products leave the public catalog and cannot be purchased. Payment amounts are not shown here."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/merchandise/orders">
            <Button variant="secondary">Orders</Button>
          </Link>
          <Link href="/admin/merchandise/print-on-demand">
            <Button variant="secondary">Print on demand</Button>
          </Link>
          <Link href="/admin/merchandise/reviews">
            <Button variant="secondary">Reviews</Button>
          </Link>
          <Link href="/admin/merchandise/reports">
            <Button variant="secondary">Reports</Button>
          </Link>
          <Link href="/admin/merchandise/revenue">
            <Button variant="secondary">Revenue</Button>
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
            {items.length} product{items.length === 1 ? "" : "s"}
          </span>
        }
      >
        <Input
          label="Search"
          placeholder="Product name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Select
          label="Status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="all">All statuses</option>
          {PRODUCT_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </Select>
        <Select
          label="Moderation"
          value={modFilter}
          onChange={(e) => setModFilter(e.target.value)}
        >
          <option value="all">All moderation</option>
          {MOD_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </Select>
        <Select
          label="Sponsor branding"
          value={sponsorFilter}
          onChange={(e) => setSponsorFilter(e.target.value)}
        >
          <option value="all">All products</option>
          <option value="yes">Sponsor-branded only</option>
          <option value="no">Not sponsor-branded</option>
        </Select>
      </FilterBar>

      {loading && !error ? <SkeletonLoader lines={5} /> : null}

      {!loading && items.length === 0 && !error ? (
        <EmptyState
          title="No merchandise"
          description="No products match these filters, or hosts have not listed merch yet."
        />
      ) : !loading ? (
        <DataTable
          rows={items}
          rowKey={(item) => item.id}
          emptyTitle="No matching products"
          emptyDescription="Try a different filter combination."
          columns={[
            {
              key: "name",
              header: "Product",
              primary: true,
              cell: (item) => (
                <div className="space-y-1">
                  <p className="font-semibold text-foreground">{item.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {formatNgn(Number(item.base_price))}
                  </p>
                  {item.is_sponsor_branded ? (
                    <p className="text-xs font-semibold text-foreground">
                      Sponsor-branded
                      {item.sponsor_brand_name
                        ? ` · ${item.sponsor_brand_name}`
                        : ""}
                    </p>
                  ) : null}
                  {item.moderation_note ? (
                    <p className="text-xs text-muted-foreground">
                      Reason: {item.moderation_note}
                    </p>
                  ) : null}
                </div>
              ),
            },
            {
              key: "host",
              header: "Host",
              cell: (item) => (
                <div className="space-y-0.5 text-sm">
                  <p className="font-medium text-foreground">
                    {item.host_name ?? "—"}
                  </p>
                  <p className="text-muted-foreground">
                    {item.host_status ?? "—"}
                  </p>
                </div>
              ),
            },
            {
              key: "event",
              header: "Event",
              cell: (item) => (
                <div className="space-y-0.5 text-sm">
                  <p className="font-medium text-foreground">
                    {item.event_title ?? "—"}
                  </p>
                  <p className="text-muted-foreground">
                    {item.event_status ?? "—"}
                  </p>
                </div>
              ),
            },
            {
              key: "status",
              header: "Status",
              cell: (item) => (
                <div className="flex flex-wrap gap-1.5">
                  <StatusBadge status={item.status} />
                  <StatusBadge status={item.moderation_status ?? "clear"} />
                </div>
              ),
            },
            {
              key: "sales",
              header: "Sales",
              cell: (item) => (
                <span className="text-sm text-foreground">
                  {item.sold_count ?? 0}
                </span>
              ),
            },
            {
              key: "reports",
              header: "Reports",
              cell: (item) => (
                <div className="space-y-0.5 text-sm text-muted-foreground">
                  <p className="text-foreground">{item.report_count ?? 0} total</p>
                  {(item.open_report_count ?? 0) > 0 ? (
                    <p>{item.open_report_count} open</p>
                  ) : null}
                </div>
              ),
            },
            {
              key: "created",
              header: "Created",
              cell: (item) => (
                <span className="text-sm text-muted-foreground">
                  {formatDate(item.created_at)}
                </span>
              ),
            },
            {
              key: "reason",
              header: "Reason",
              cell: (item) => (
                <Textarea
                  label="Moderation reason"
                  rows={2}
                  value={notes[item.id] ?? ""}
                  onChange={(e) =>
                    setNotes((prev) => ({ ...prev, [item.id]: e.target.value }))
                  }
                  placeholder="Required for hide / archive / restore"
                />
              ),
            },
            {
              key: "actions",
              header: "Actions",
              cell: (item) => {
                const busy = busyId === item.id;
                const mod = item.moderation_status ?? "clear";
                const canHide = mod !== "hidden" && mod !== "removed";
                const canRestore = mod === "hidden" || mod === "removed";
                const canArchive =
                  item.status !== "archived" && mod !== "removed";
                return (
                  <div className="flex flex-wrap justify-end gap-1.5 md:justify-start">
                    <Link href={`/admin/merchandise/${item.id}`}>
                      <Button size="sm" variant="secondary" disabled={busy}>
                        View
                      </Button>
                    </Link>
                    {canHide ? (
                      <ConfirmAction
                        label="Hide"
                        title="Hide this listing?"
                        description={`Hide “${item.name}” from the public catalog. Requires a reason.`}
                        confirmLabel="Hide listing"
                        tone="danger"
                        disabled={busy}
                        busy={busy}
                        onConfirm={() => onModerate(item.id, "hide")}
                      />
                    ) : null}
                    {canRestore ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy}
                        onClick={() => void onModerate(item.id, "restore")}
                      >
                        Restore
                      </Button>
                    ) : null}
                    {canArchive ? (
                      <ConfirmAction
                        label="Archive"
                        title="Archive this listing?"
                        description={`Archive “${item.name}” (not public, not purchasable). Requires a reason.`}
                        confirmLabel="Archive listing"
                        tone="danger"
                        disabled={busy}
                        busy={busy}
                        onConfirm={() => onModerate(item.id, "archive")}
                      />
                    ) : null}
                    <ConfirmAction
                      label="Deactivate unsafe"
                      title="Deactivate for suspended host/event?"
                      description="Only succeeds when the host or event is already suspended/cancelled. Pauses and hides the listing."
                      confirmLabel="Deactivate"
                      tone="danger"
                      disabled={busy}
                      busy={busy}
                      onConfirm={() => onDeactivateUnsafe(item.id)}
                    />
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
