"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
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
import { formatNgn } from "@/lib/format";
import type { VaultAdminItem } from "@/lib/types/vault";
import { fetchAdminVaultItems, moderateVaultItem } from "@/lib/vault-api";

const ITEM_STATUSES = [
  "draft",
  "published",
  "scheduled",
  "expired",
  "archived",
  "hidden_by_admin",
] as const;

const ACCESS_TYPES = [
  "free",
  "followers_only",
  "ticket_holder_only",
  "checked_in_attendee_only",
  "vip_ticket_holder_only",
  "one_time_unlock",
  "invite_only",
] as const;

const MOD_STATUSES = ["none", "flagged", "approved", "removed"] as const;

const REASON_REQUIRED = new Set(["hide", "archive", "remove", "restore"]);

export default function AdminVaultPage() {
  const [items, setItems] = useState<VaultAdminItem[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [modFilter, setModFilter] = useState("all");
  const [accessFilter, setAccessFilter] = useState("all");
  const [hostFilter, setHostFilter] = useState("");
  const [debouncedHost, setDebouncedHost] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => window.clearTimeout(t);
  }, [search]);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedHost(hostFilter.trim()), 300);
    return () => window.clearTimeout(t);
  }, [hostFilter]);

  const load = useCallback(async () => {
    const rows = await fetchAdminVaultItems({
      status: statusFilter === "all" ? undefined : statusFilter,
      moderation_status: modFilter === "all" ? undefined : modFilter,
      access_type: accessFilter === "all" ? undefined : accessFilter,
      host_username: debouncedHost || undefined,
      q: debouncedSearch || undefined,
      limit: 200,
    });
    setItems(rows);
  }, [statusFilter, modFilter, accessFilter, debouncedHost, debouncedSearch]);

  useEffect(() => {
    let active = true;
    void (async () => {
      setLoading(true);
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load Vault");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function onModerate(id: string, action: string) {
    const itemNote = notes[id]?.trim() ?? "";
    if (REASON_REQUIRED.has(action) && !itemNote) {
      setError("Moderation reason is required for hide, archive, remove, and restore");
      return;
    }
    setError(null);
    setBusyId(id);
    try {
      await moderateVaultItem(id, action, itemNote || undefined);
      setNotes((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      const labels: Record<string, string> = {
        flag: "flagged",
        approve: "approved",
        hide: "hidden",
        archive: "archived",
        remove: "removed",
        restore: "restored",
      };
      setNote(`Vault item ${labels[action] ?? "updated"}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Moderation failed");
    } finally {
      setBusyId(null);
    }
  }

  function renderActions(item: VaultAdminItem) {
    const busy = busyId === item.id;
    return (
      <div className="flex flex-wrap justify-end gap-1.5 md:justify-start">
        <Button
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => void onModerate(item.id, "flag")}
        >
          Flag
        </Button>
        <Button
          size="sm"
          disabled={busy}
          onClick={() => void onModerate(item.id, "approve")}
        >
          Approve
        </Button>
        <ConfirmAction
          label="Hide"
          title="Hide this Vault item?"
          description={`Hide “${item.title}” from the public Vault (hidden_by_admin). Requires a moderation reason.`}
          confirmLabel="Hide item"
          tone="danger"
          disabled={busy}
          busy={busy}
          onConfirm={() => onModerate(item.id, "hide")}
        />
        <ConfirmAction
          label="Archive"
          title="Archive this Vault item?"
          description={`Archive “${item.title}” and remove it from the public Vault. Requires a moderation reason.`}
          confirmLabel="Archive item"
          tone="danger"
          disabled={busy}
          busy={busy}
          onConfirm={() => onModerate(item.id, "archive")}
        />
        <Button
          size="sm"
          variant="ghost"
          disabled={busy}
          onClick={() => void onModerate(item.id, "restore")}
        >
          Restore
        </Button>
      </div>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Vault moderation"
      description="Filter, hide, archive, or restore Vault drops. Unlock summaries are read-only. Actions require vault.moderate and are audited."
      actions={
        <Link href="/admin">
          <Button variant="secondary">Admin home</Button>
        </Link>
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
            {items.length} item{items.length === 1 ? "" : "s"}
          </span>
        }
      >
        <Input
          label="Search"
          placeholder="Title, host, content type…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Input
          label="Host username"
          placeholder="e.g. vault-host"
          value={hostFilter}
          onChange={(e) => setHostFilter(e.target.value)}
        />
        <Select
          label="Item status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="all">All statuses</option>
          {ITEM_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status.replace(/_/g, " ")}
            </option>
          ))}
        </Select>
        <Select
          label="Access type"
          value={accessFilter}
          onChange={(e) => setAccessFilter(e.target.value)}
        >
          <option value="all">All access types</option>
          {ACCESS_TYPES.map((type) => (
            <option key={type} value={type}>
              {type.replace(/_/g, " ")}
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
              {status.replace(/_/g, " ")}
            </option>
          ))}
        </Select>
      </FilterBar>

      {loading && !error ? <SkeletonLoader lines={5} /> : null}

      {!loading && items.length === 0 && !error ? (
        <EmptyState
          title="No Vault items"
          description="No drops match these filters, or hosts have not published Vault content yet."
        />
      ) : !loading ? (
        <DataTable
          rows={items}
          rowKey={(item) => item.id}
          emptyTitle="No matching Vault items"
          emptyDescription="Try a different filter combination."
          columns={[
            {
              key: "title",
              header: "Item",
              primary: true,
              cell: (item) => (
                <div className="space-y-1">
                  <p className="font-semibold text-foreground">{item.title}</p>
                  <p className="text-sm text-muted-foreground">
                    @{item.host_username ?? "—"} ·{" "}
                    {(item.access_type || item.access?.access_type || "—").replace(
                      /_/g,
                      " ",
                    )}{" "}
                    · {item.content_type.replace(/_/g, " ")}
                  </p>
                  {item.preview_text ? (
                    <p className="line-clamp-2 text-sm text-muted-foreground">
                      {item.preview_text}
                    </p>
                  ) : null}
                  {item.moderation_note ? (
                    <p className="text-xs text-muted-foreground">
                      Last reason: {item.moderation_note}
                    </p>
                  ) : null}
                </div>
              ),
            },
            {
              key: "status",
              header: "Status",
              cell: (item) => (
                <div className="flex flex-wrap gap-1.5">
                  <StatusBadge status={item.status} />
                  <StatusBadge status={item.moderation_status} />
                </div>
              ),
            },
            {
              key: "unlocks",
              header: "Unlocks",
              cell: (item) => (
                <div className="space-y-0.5 text-sm">
                  <p className="font-semibold text-foreground">
                    {item.unlock_count ?? 0} paid
                  </p>
                  <p className="text-muted-foreground">
                    {item.grant_count ?? 0} grants · {item.view_count ?? 0} views
                  </p>
                  <p className="font-semibold">
                    {formatNgn(item.gross_revenue ?? 0)}
                  </p>
                </div>
              ),
            },
            {
              key: "reports",
              header: "Reports",
              cell: (item) =>
                (item.report_count ?? 0) > 0 ? (
                  <span className="font-semibold text-foreground">
                    {item.report_count}
                  </span>
                ) : (
                  <span className="text-sm text-muted-foreground">None</span>
                ),
            },
            {
              key: "note",
              header: "Reason",
              cell: (item) => (
                <Textarea
                  aria-label={`Moderation reason for ${item.title}`}
                  hint="Required for hide / archive / restore"
                  value={notes[item.id] ?? ""}
                  onChange={(e) =>
                    setNotes((prev) => ({ ...prev, [item.id]: e.target.value }))
                  }
                  className="min-h-[64px] text-sm"
                />
              ),
            },
            {
              key: "actions",
              header: "Actions",
              cell: (item) => renderActions(item),
            },
          ]}
          mobileCard={(item) => (
            <Card className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-bold text-foreground">{item.title}</h3>
                <StatusBadge status={item.status} />
                <StatusBadge status={item.moderation_status} />
              </div>
              <p className="text-sm text-muted-foreground">
                @{item.host_username} ·{" "}
                {(item.access_type || item.access?.access_type || "—").replace(
                  /_/g,
                  " ",
                )}
              </p>
              <p className="text-sm text-muted-foreground">
                {item.unlock_count ?? 0} paid unlocks · {formatNgn(item.gross_revenue ?? 0)}{" "}
                · reports {item.report_count ?? 0}
              </p>
              {item.moderation_note ? (
                <p className="text-xs text-muted-foreground">
                  Last reason: {item.moderation_note}
                </p>
              ) : null}
              <Textarea
                label="Moderation reason"
                hint="Required for hide / archive / restore"
                value={notes[item.id] ?? ""}
                onChange={(e) =>
                  setNotes((prev) => ({ ...prev, [item.id]: e.target.value }))
                }
                className="min-h-[72px]"
              />
              {renderActions(item)}
            </Card>
          )}
        />
      ) : null}
    </DashboardShell>
  );
}
