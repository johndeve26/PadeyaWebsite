"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

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
import { fetchAdminMemories, moderateMemory } from "@/lib/memories-api";
import type { EventMemory } from "@/lib/types/memories";

export default function AdminMemoriesPage() {
  const [items, setItems] = useState<EventMemory[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [modFilter, setModFilter] = useState("all");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setItems(await fetchAdminMemories());
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load memories");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const modStatuses = useMemo(() => {
    const set = new Set(items.map((i) => i.moderation_status));
    return Array.from(set).sort();
  }, [items]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((item) => {
      if (modFilter !== "all" && item.moderation_status !== modFilter) return false;
      if (!q) return true;
      const haystack = [
        item.event_title,
        item.host_username,
        item.host_display_name,
        item.host_recap_note,
        item.city,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [items, search, modFilter]);

  async function onModerate(
    id: string,
    action: "hide" | "unhide" | "flag" | "approve",
  ) {
    setError(null);
    setBusyId(id);
    try {
      const itemNote = notes[id]?.trim();
      await moderateMemory(id, { action, note: itemNote || undefined });
      setNotes((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      const labels: Record<string, string> = {
        flag: "flagged",
        approve: "approved",
        hide: "hidden",
        unhide: "unhidden",
      };
      setNote(`Memory ${labels[action] ?? "updated"}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Moderation failed");
    } finally {
      setBusyId(null);
    }
  }

  function renderActions(item: EventMemory) {
    const busy = busyId === item.id;
    return (
      <div className="flex flex-wrap gap-2">
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
          title="Hide this memory page?"
          description={`Hide the public memory for “${item.event_title}”. The share link will no longer be visible.`}
          confirmLabel="Hide memory"
          tone="danger"
          disabled={busy}
          busy={busy}
          onConfirm={() => onModerate(item.id, "hide")}
        />
        <Button
          size="sm"
          variant="ghost"
          disabled={busy}
          onClick={() => void onModerate(item.id, "unhide")}
        >
          Unhide
        </Button>
        <Link href={item.share_path}>
          <Button size="sm" variant="ghost">
            Open
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Event Memories moderation"
      description="Hide inappropriate public memory pages. Actions are audited."
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

      {loading && !error ? <SkeletonLoader lines={5} /> : null}

      {!loading && items.length > 0 ? (
        <FilterBar
          trailing={
            <span className="text-sm text-muted-foreground">
              {filtered.length} of {items.length} memories
            </span>
          }
        >
          <Input
            label="Search"
            placeholder="Event, host, recap…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Select
            label="Moderation status"
            value={modFilter}
            onChange={(e) => setModFilter(e.target.value)}
          >
            <option value="all">All statuses</option>
            {modStatuses.map((status) => (
              <option key={status} value={status}>
                {status.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </FilterBar>
      ) : null}

      {!loading && items.length === 0 && !error ? (
        <EmptyState
          title="No event memories"
          description="Published memory pages from hosts will appear here for moderation."
        />
      ) : !loading ? (
        <DataTable
          rows={filtered}
          rowKey={(item) => item.id}
          emptyTitle="No matching memories"
          emptyDescription="Try a different search or moderation filter."
          columns={[
            {
              key: "event",
              header: "Event",
              primary: true,
              cell: (item) => (
                <div className="space-y-1">
                  <p className="font-semibold text-foreground">{item.event_title}</p>
                  <p className="text-sm text-muted-foreground">
                    @{item.host_username} · {item.city ?? "—"}
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
                  <StatusBadge status={item.moderation_status} />
                </div>
              ),
            },
            {
              key: "recap",
              header: "Recap",
              cell: (item) => (
                <p className="line-clamp-2 max-w-xs text-sm text-muted-foreground">
                  {item.host_recap_note || "No recap note"}
                </p>
              ),
            },
            {
              key: "note",
              header: "Note",
              cell: (item) => (
                <Textarea
                  aria-label={`Moderation note for ${item.event_title}`}
                  value={notes[item.id] ?? ""}
                  onChange={(e) =>
                    setNotes((prev) => ({ ...prev, [item.id]: e.target.value }))
                  }
                  className="min-h-[64px] text-sm"
                  placeholder="Optional audit note…"
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
                <h3 className="font-bold text-foreground">{item.event_title}</h3>
                <StatusBadge status={item.status} />
                <StatusBadge status={item.moderation_status} />
              </div>
              <p className="text-sm text-muted-foreground">@{item.host_username}</p>
              <p className="text-sm text-muted-foreground">
                {item.host_recap_note || "No recap note"}
              </p>
              <Textarea
                label="Moderation note (optional)"
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
