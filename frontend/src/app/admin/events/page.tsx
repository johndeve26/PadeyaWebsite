"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  ConfirmAction,
  DataTable,
  FilterBar,
  Input,
  Modal,
  Select,
  SkeletonLoader,
  StatusBadge,
  Textarea,
  useToast,
} from "@/components/ui";
import {
  clearEventPadeyaPick,
  featureEvent,
  setEventPadeyaPick,
  unfeatureEvent,
} from "@/lib/admin-lifecycle-api";
import { ApiError } from "@/lib/api";
import {
  archiveEvent,
  cancelEvent,
  clearEventFlag,
  discardEvent,
  fetchAdminEvents,
  flagEvent,
  pauseEvent,
  resumeEvent,
} from "@/lib/events-api";
import { formatDate } from "@/lib/format";
import { fetchFeaturedPlacements } from "@/lib/placements-api";
import type { EventItem, EventStatus } from "@/lib/types/events";

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "all", label: "All statuses" },
  { value: "published", label: "Published" },
  { value: "draft", label: "Draft" },
  { value: "paused", label: "Paused" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "rejected", label: "Rejected" },
  { value: "archived", label: "Archived" },
];

const FLAG_OPTIONS = [
  { value: "all", label: "Any flag" },
  { value: "flagged", label: "Flagged only" },
  { value: "clear", label: "Not flagged" },
];

type PickSlotInfo = { slot_number: number; slot_label: string };

function canDeactivate(e: EventItem): boolean {
  return e.status === "published";
}

function canRestore(e: EventItem): boolean {
  return e.status === "paused";
}

function canCancel(e: EventItem): boolean {
  return !["completed", "cancelled", "archived"].includes(e.status);
}

function canArchive(e: EventItem): boolean {
  return ["draft", "rejected", "completed", "cancelled"].includes(e.status);
}

function canDiscard(e: EventItem): boolean {
  return e.status === "draft" || e.status === "rejected";
}

function isSelectable(e: EventItem): boolean {
  return canDeactivate(e) || canCancel(e) || canArchive(e) || canDiscard(e);
}

export default function AdminEventsPage() {
  const toast = useToast();
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [pickByEventId, setPickByEventId] = useState<
    Record<string, PickSlotInfo>
  >({});
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [flagFilter, setFlagFilter] = useState("all");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [flagTarget, setFlagTarget] = useState<EventItem | null>(null);
  const [flagReason, setFlagReason] = useState("");
  const [flagError, setFlagError] = useState<string | null>(null);
  const [pickTarget, setPickTarget] = useState<EventItem | null>(null);

  const loadPicks = useCallback(async () => {
    const slots = await fetchFeaturedPlacements({ context_type: "homepage" });
    const map: Record<string, PickSlotInfo> = {};
    for (const slot of slots) {
      if (
        slot.event_id &&
        (slot.status === "active" || slot.status === "scheduled")
      ) {
        map[slot.event_id] = {
          slot_number: slot.slot_number,
          slot_label: slot.slot_label,
        };
      }
    }
    setPickByEventId(map);
  }, []);

  async function loadEvents() {
    const data = await fetchAdminEvents();
    setEvents(data);
    await loadPicks().catch(() => setPickByEventId({}));
  }

  useEffect(() => {
    setSelectedIds(new Set());
  }, [search, statusFilter, flagFilter]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchAdminEvents();
        if (!active) return;
        setEvents(data);
        try {
          await loadPicks();
        } catch {
          if (active) setPickByEventId({});
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [loadPicks]);

  const filtered = useMemo(() => {
    if (!events) return [];
    const q = search.trim().toLowerCase();
    return events.filter((e) => {
      if (statusFilter !== "all" && e.status !== statusFilter) return false;
      const isFlagged = Boolean(e.admin_flagged || e.admin_flagged_at);
      if (flagFilter === "flagged" && !isFlagged) return false;
      if (flagFilter === "clear" && isFlagged) return false;
      if (!q) return true;
      const haystack = [e.title, e.host_display_name, e.city, e.venue_name]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [events, search, statusFilter, flagFilter]);

  const selectableIds = useMemo(
    () => filtered.filter(isSelectable).map((e) => e.id),
    [filtered],
  );

  const selectedDeactivateCount = useMemo(
    () =>
      [...selectedIds].filter((id) => {
        const row = filtered.find((e) => e.id === id);
        return row ? canDeactivate(row) : false;
      }).length,
    [selectedIds, filtered],
  );

  const selectedCancelCount = useMemo(
    () =>
      [...selectedIds].filter((id) => {
        const row = filtered.find((e) => e.id === id);
        return row ? canCancel(row) : false;
      }).length,
    [selectedIds, filtered],
  );

  const selectedArchiveCount = useMemo(
    () =>
      [...selectedIds].filter((id) => {
        const row = filtered.find((e) => e.id === id);
        return row ? canArchive(row) : false;
      }).length,
    [selectedIds, filtered],
  );

  const selectedCount =
    selectedDeactivateCount + selectedCancelCount + selectedArchiveCount;

  const allSelectableChecked =
    selectableIds.length > 0 &&
    selectableIds.every((id) => selectedIds.has(id));
  const someSelectableChecked =
    selectableIds.some((id) => selectedIds.has(id)) && !allSelectableChecked;

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    setSelectedIds((prev) => {
      if (allSelectableChecked) {
        const next = new Set(prev);
        for (const id of selectableIds) next.delete(id);
        return next;
      }
      const next = new Set(prev);
      for (const id of selectableIds) next.add(id);
      return next;
    });
  }

  async function runBulk(
    targets: string[],
    action: (id: string) => Promise<unknown>,
    labels: { success: string; fail: string; mixed: string },
  ) {
    if (targets.length === 0) return;
    setBulkBusy(true);
    let ok = 0;
    let fail = 0;
    let lastError: string | null = null;
    try {
      for (const id of targets) {
        try {
          await action(id);
          ok += 1;
        } catch (err) {
          fail += 1;
          lastError = err instanceof ApiError ? err.detail : "Try again";
        }
      }
      setSelectedIds(new Set());
      await loadEvents();
      if (fail === 0) {
        toast.push({ tone: "success", title: `${ok} ${labels.success}` });
      } else if (ok === 0) {
        toast.push({
          tone: "danger",
          title: labels.fail,
          description: lastError ?? "Try again",
        });
      } else {
        toast.push({
          tone: "danger",
          title: labels.mixed.replace("{ok}", String(ok)).replace("{fail}", String(fail)),
          description: lastError ?? "Review remaining events and retry",
        });
      }
    } finally {
      setBulkBusy(false);
    }
  }

  async function onDeactivate(id: string) {
    setBusyId(id);
    try {
      await pauseEvent(id);
      toast.push({ tone: "success", title: "Event deactivated (paused)" });
      setSelectedIds((prev) => {
        if (!prev.has(id)) return prev;
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      await loadEvents();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Deactivate failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onRestore(id: string) {
    setBusyId(id);
    try {
      await resumeEvent(id);
      toast.push({ tone: "success", title: "Event restored (published)" });
      await loadEvents();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Restore failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onCancel(id: string) {
    setBusyId(id);
    try {
      await cancelEvent(id);
      toast.push({ tone: "success", title: "Event cancelled" });
      setSelectedIds((prev) => {
        if (!prev.has(id)) return prev;
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      await loadEvents();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Cancel failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onArchive(id: string) {
    setBusyId(id);
    try {
      await archiveEvent(id);
      toast.push({ tone: "success", title: "Event archived" });
      setSelectedIds((prev) => {
        if (!prev.has(id)) return prev;
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      await loadEvents();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Archive failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onDiscard(id: string) {
    setBusyId(id);
    try {
      await discardEvent(id);
      toast.push({ tone: "success", title: "Draft deleted" });
      setSelectedIds((prev) => {
        if (!prev.has(id)) return prev;
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      await loadEvents();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Delete failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function toggleFeatured(event: EventItem) {
    setBusyId(event.id);
    try {
      if (event.featured) {
        await unfeatureEvent(event.id);
        toast.push({ tone: "success", title: "Event unfeatured" });
      } else {
        await featureEvent(event.id);
        toast.push({ tone: "success", title: "Event featured" });
      }
      await loadEvents();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Feature toggle failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function addPadeyaPick(event: EventItem, slot?: 1 | 2) {
    setBusyId(event.id);
    try {
      await setEventPadeyaPick(event.id, {
        context_type: "homepage",
        slot_number: slot,
      });
      toast.push({
        tone: "success",
        title: "Added to Pàdéyá Picks",
        description: "Homepage spotlight updated.",
      });
      setPickTarget(null);
      await loadEvents();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Try again";
      if (
        err instanceof ApiError &&
        (err.status === 409 || /both.*slots are filled/i.test(detail))
      ) {
        setPickTarget(event);
      } else {
        toast.push({
          tone: "danger",
          title: "Pàdéyá Pick failed",
          description: detail,
        });
      }
    } finally {
      setBusyId(null);
    }
  }

  async function removePadeyaPick(event: EventItem) {
    setBusyId(event.id);
    try {
      await clearEventPadeyaPick(event.id, { context_type: "homepage" });
      toast.push({ tone: "success", title: "Removed from Pàdéyá Picks" });
      await loadEvents();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Remove pick failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onSubmitFlag() {
    if (!flagTarget) return;
    const trimmed = flagReason.trim();
    if (trimmed.length < 3) {
      setFlagError("Enter at least 3 characters.");
      return;
    }
    setBusyId(flagTarget.id);
    try {
      await flagEvent(flagTarget.id, trimmed);
      toast.push({ tone: "success", title: "Event flagged" });
      setFlagTarget(null);
      setFlagReason("");
      setFlagError(null);
      await loadEvents();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Flag failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onClearFlag(event: EventItem) {
    setBusyId(event.id);
    try {
      await clearEventFlag(event.id);
      toast.push({ tone: "success", title: "Flag cleared" });
      await loadEvents();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Clear flag failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  const flaggedCount =
    events?.filter((e) => e.admin_flagged || e.admin_flagged_at).length ?? 0;
  const pickCount = Object.keys(pickByEventId).length;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="All events"
      description="Review listings, pause or cancel, archive ended nights, and manage featured placement."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/events/picks">
            <Button variant="secondary">
              Pàdéyá Picks{pickCount > 0 ? ` (${pickCount})` : ""}
            </Button>
          </Link>
          <Link href="/admin/events/review">
            <Button>
              Review queue{flaggedCount > 0 ? ` (${flaggedCount})` : ""}
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Failed to load events">
          {error}
        </Alert>
      ) : null}

      {events ? (
        <Alert tone="info" title="Soft lifecycle only">
          Deactivate pauses a live listing. Cancel ends sales and notifies
          ticket holders. Archive is soft end-of-life for completed/cancelled
          (or unused drafts). Hard delete only removes unused draft/rejected
          events with no sales.
        </Alert>
      ) : null}

      {events && flaggedCount > 0 ? (
        <Alert tone="info" title="Flagged listings">
          {flaggedCount} event{flaggedCount === 1 ? "" : "s"} currently flagged
          for ops attention (listings stay live until rejected or paused).
        </Alert>
      ) : null}

      {events ? (
        <>
          <FilterBar
            trailing={
              <span className="text-sm text-muted-foreground">
                {filtered.length} of {events.length} events
              </span>
            }
          >
            <Input
              label="Search"
              placeholder="Title, host, city…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Select
              label="Status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
            <Select
              label="Flags"
              value={flagFilter}
              onChange={(e) => setFlagFilter(e.target.value)}
            >
              {FLAG_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
          </FilterBar>

          {filtered.length > 0 ? (
            <div className="mb-4 flex flex-col gap-3 rounded-[var(--radius-lg)] border border-border bg-card px-4 py-3 sm:flex-row sm:items-center sm:justify-between dark:bg-surface-elevated">
              <div className="flex flex-wrap items-center gap-4">
                <label className="inline-flex cursor-pointer items-center gap-2.5 text-sm text-foreground">
                  <input
                    id="admin-events-select-all"
                    type="checkbox"
                    checked={allSelectableChecked}
                    ref={(el) => {
                      if (el) el.indeterminate = someSelectableChecked;
                    }}
                    onChange={() => toggleSelectAll()}
                    disabled={selectableIds.length === 0 || bulkBusy}
                    className="h-4 w-4 accent-[color:var(--brand-green)] disabled:cursor-not-allowed disabled:opacity-40"
                  />
                  <span>Select all on page</span>
                </label>
                <span className="text-sm text-muted-foreground">
                  {selectedCount > 0
                    ? `${selectedIds.size} selected`
                    : "Select events to deactivate, cancel, or archive"}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                <ConfirmAction
                  label="Deactivate selected"
                  title={`Deactivate ${selectedDeactivateCount} published event${selectedDeactivateCount === 1 ? "" : "s"}?`}
                  description="Pauses sales on each selected published listing. Hosts can still manage the event; resume restores it."
                  confirmLabel="Deactivate selected"
                  tone="danger"
                  size="sm"
                  disabled={selectedDeactivateCount === 0}
                  busy={bulkBusy}
                  onConfirm={() =>
                    runBulk(
                      [...selectedIds].filter((id) => {
                        const row = filtered.find((e) => e.id === id);
                        return row ? canDeactivate(row) : false;
                      }),
                      pauseEvent,
                      {
                        success: "event(s) deactivated",
                        fail: "Bulk deactivate failed",
                        mixed: "{ok} deactivated, {fail} failed",
                      },
                    )
                  }
                />
                <ConfirmAction
                  label="Cancel selected"
                  title={`Cancel ${selectedCancelCount} event${selectedCancelCount === 1 ? "" : "s"}?`}
                  description="Ends the listing and notifies active ticket holders. Completed/cancelled/archived events are skipped."
                  confirmLabel="Cancel selected"
                  tone="danger"
                  size="sm"
                  disabled={selectedCancelCount === 0}
                  busy={bulkBusy}
                  onConfirm={() =>
                    runBulk(
                      [...selectedIds].filter((id) => {
                        const row = filtered.find((e) => e.id === id);
                        return row ? canCancel(row) : false;
                      }),
                      cancelEvent,
                      {
                        success: "event(s) cancelled",
                        fail: "Bulk cancel failed",
                        mixed: "{ok} cancelled, {fail} failed",
                      },
                    )
                  }
                />
                <ConfirmAction
                  label="Archive selected"
                  title={`Archive ${selectedArchiveCount} event${selectedArchiveCount === 1 ? "" : "s"}?`}
                  description="Soft end-of-life for completed, cancelled, or unused draft/rejected events. Paid history stays."
                  confirmLabel="Archive selected"
                  tone="danger"
                  size="sm"
                  disabled={selectedArchiveCount === 0}
                  busy={bulkBusy}
                  onConfirm={() =>
                    runBulk(
                      [...selectedIds].filter((id) => {
                        const row = filtered.find((e) => e.id === id);
                        return row ? canArchive(row) : false;
                      }),
                      archiveEvent,
                      {
                        success: "event(s) archived",
                        fail: "Bulk archive failed",
                        mixed: "{ok} archived, {fail} failed",
                      },
                    )
                  }
                />
              </div>
            </div>
          ) : null}

          <DataTable
            rows={filtered}
            rowKey={(e) => e.id}
            emptyTitle="No matching events"
            emptyDescription={
              search || statusFilter !== "all" || flagFilter !== "all"
                ? "Try a different search or filter."
                : "When hosts create events, they appear here."
            }
            columns={[
              {
                key: "select",
                header: "",
                className: "w-10",
                cell: (e) => {
                  const selectable = isSelectable(e);
                  return (
                    <input
                      type="checkbox"
                      checked={selectedIds.has(e.id)}
                      disabled={!selectable || bulkBusy}
                      onChange={() => toggleSelect(e.id)}
                      aria-label={`Select ${e.title}`}
                      className="h-4 w-4 accent-[color:var(--brand-green)] disabled:cursor-not-allowed disabled:opacity-40"
                    />
                  );
                },
              },
              {
                key: "title",
                header: "Event",
                primary: true,
                cell: (e) => (
                  <div className="space-y-0.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-foreground">
                        {e.title}
                      </span>
                      {e.admin_flagged || e.admin_flagged_at ? (
                        <Badge tone="warning" size="sm">
                          Flagged
                        </Badge>
                      ) : null}
                      {pickByEventId[e.id] ? (
                        <Badge tone="accent" size="sm">
                          Pàdéyá Pick
                        </Badge>
                      ) : null}
                    </div>
                    {e.city ? (
                      <p className="text-sm text-muted-foreground">{e.city}</p>
                    ) : null}
                  </div>
                ),
              },
              {
                key: "host",
                header: "Host",
                cell: (e) => e.host_display_name ?? "—",
              },
              {
                key: "start",
                header: "Starts",
                cell: (e) => formatDate(e.start_datetime),
              },
              {
                key: "status",
                header: "Status",
                cell: (e) => <StatusBadge status={e.status as EventStatus} />,
              },
              {
                key: "featured",
                header: "Featured",
                cell: (e) =>
                  e.featured ? (
                    <StatusBadge status="active" label="Featured" />
                  ) : (
                    <span className="text-sm text-muted-foreground">—</span>
                  ),
              },
              {
                key: "padeya_pick",
                header: "Pàdéyá Pick",
                cell: (e) => {
                  const pick = pickByEventId[e.id];
                  if (!pick) {
                    return (
                      <span className="text-sm text-muted-foreground">—</span>
                    );
                  }
                  return (
                    <StatusBadge
                      status="active"
                      label={pick.slot_label.replace(" Spotlight", "")}
                    />
                  );
                },
              },
              {
                key: "actions",
                header: "Actions",
                cell: (e) => {
                  const isFlagged = Boolean(
                    e.admin_flagged || e.admin_flagged_at,
                  );
                  const isPick = Boolean(pickByEventId[e.id]);
                  const rowBusy = busyId === e.id || bulkBusy;
                  return (
                    <div className="flex flex-wrap gap-2">
                      <Link href={`/admin/events/${e.id}/review`}>
                        <Button size="sm" variant="secondary">
                          Review
                        </Button>
                      </Link>
                      {canDeactivate(e) ? (
                        <ConfirmAction
                          label="Deactivate"
                          title="Deactivate (pause) this event?"
                          description={`Pauses sales for “${e.title}”. Resume restores the published listing.`}
                          confirmLabel="Deactivate"
                          tone="danger"
                          size="sm"
                          busy={rowBusy}
                          onConfirm={() => onDeactivate(e.id)}
                        />
                      ) : null}
                      {canRestore(e) ? (
                        <ConfirmAction
                          label="Restore"
                          title="Restore this paused event?"
                          description={`Publishes “${e.title}” again.`}
                          confirmLabel="Restore"
                          size="sm"
                          busy={rowBusy}
                          onConfirm={() => onRestore(e.id)}
                        />
                      ) : null}
                      {canCancel(e) ? (
                        <ConfirmAction
                          label="Cancel"
                          title="Cancel this event?"
                          description={`Ends “${e.title}” and notifies active ticket holders. Prefer archive after completion when the night already ended.`}
                          confirmLabel="Cancel event"
                          tone="danger"
                          size="sm"
                          busy={rowBusy}
                          onConfirm={() => onCancel(e.id)}
                        />
                      ) : null}
                      {canArchive(e) ? (
                        <ConfirmAction
                          label="Archive"
                          title="Archive this event?"
                          description={`Soft end-of-life for “${e.title}”. Commerce history stays; hard delete is not used for paid events.`}
                          confirmLabel="Archive"
                          tone="danger"
                          size="sm"
                          busy={rowBusy}
                          onConfirm={() => onArchive(e.id)}
                        />
                      ) : null}
                      {canDiscard(e) ? (
                        <ConfirmAction
                          label="Delete draft"
                          title="Permanently delete this unused draft?"
                          description={`Hard-deletes “${e.title}” only if it has no ticket sales. Prefer archive when unsure.`}
                          confirmLabel="Delete draft"
                          tone="danger"
                          size="sm"
                          busy={rowBusy}
                          onConfirm={() => onDiscard(e.id)}
                        />
                      ) : null}
                      {isFlagged ? (
                        <ConfirmAction
                          label="Clear flag"
                          title="Clear admin flag?"
                          description={`Remove the ops flag from “${e.title}”.`}
                          confirmLabel="Clear flag"
                          size="sm"
                          busy={rowBusy}
                          onConfirm={() => onClearFlag(e)}
                        />
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={rowBusy}
                          onClick={() => {
                            setFlagTarget(e);
                            setFlagReason("");
                            setFlagError(null);
                          }}
                        >
                          Flag
                        </Button>
                      )}
                      <Link href={`/admin/events/${e.id}/buyers`}>
                        <Button size="sm" variant="ghost">
                          Buyers
                        </Button>
                      </Link>
                      <Link href={`/admin/events/${e.id}/exports`}>
                        <Button size="sm" variant="ghost">
                          Exports
                        </Button>
                      </Link>
                      <Link href={`/admin/events/${e.id}/analytics`}>
                        <Button size="sm" variant="ghost">
                          Analytics
                        </Button>
                      </Link>
                      {e.status === "published" ? (
                        isPick ? (
                          <ConfirmAction
                            label="Remove Pick"
                            title="Remove from Pàdéyá Picks?"
                            description={`“${e.title}” will leave the homepage Pàdéyá Picks spotlights.`}
                            confirmLabel="Remove Pick"
                            busy={rowBusy}
                            onConfirm={() => removePadeyaPick(e)}
                          />
                        ) : (
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={rowBusy}
                            onClick={() => void addPadeyaPick(e)}
                          >
                            Pàdéyá Pick
                          </Button>
                        )
                      ) : null}
                      {e.status === "published" ? (
                        e.featured ? (
                          <ConfirmAction
                            label="Unfeature"
                            title="Remove from featured?"
                            description={`"${e.title}" will no longer appear in featured listings.`}
                            confirmLabel="Unfeature"
                            busy={rowBusy}
                            onConfirm={() => toggleFeatured(e)}
                          />
                        ) : (
                          <ConfirmAction
                            label="Feature"
                            title="Feature this event?"
                            description={`"${e.title}" will appear in featured listings on the platform.`}
                            confirmLabel="Feature"
                            busy={rowBusy}
                            onConfirm={() => toggleFeatured(e)}
                          />
                        )
                      ) : null}
                    </div>
                  );
                },
              },
            ]}
          />
        </>
      ) : null}

      {events == null && !error ? <SkeletonLoader lines={4} /> : null}

      <Modal
        open={Boolean(flagTarget)}
        onClose={() => {
          if (busyId) return;
          setFlagTarget(null);
          setFlagReason("");
          setFlagError(null);
        }}
        title={flagTarget ? `Flag “${flagTarget.title}”?` : "Flag event"}
        description="Adds an admin flag for ops follow-up. Does not hide or unpublish the listing."
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              disabled={Boolean(busyId)}
              onClick={() => {
                setFlagTarget(null);
                setFlagReason("");
                setFlagError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              variant="danger"
              disabled={Boolean(busyId) || !flagTarget}
              onClick={() => void onSubmitFlag()}
            >
              {busyId ? "Working…" : "Flag listing"}
            </Button>
          </>
        }
      >
        <Textarea
          label="Flag reason"
          hint="Required. Stored on the event and audited."
          placeholder="Why does this listing need attention?"
          value={flagReason}
          error={flagError ?? undefined}
          onChange={(e) => {
            setFlagReason(e.target.value);
            if (flagError) setFlagError(null);
          }}
          rows={3}
        />
      </Modal>

      <Modal
        open={Boolean(pickTarget)}
        onClose={() => {
          if (busyId) return;
          setPickTarget(null);
        }}
        title={
          pickTarget
            ? `Replace a Pàdéyá Pick with “${pickTarget.title}”?`
            : "Pàdéyá Pick"
        }
        description="Both homepage spotlight slots are filled. Choose which slot to replace, or manage picks on the dedicated page."
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              disabled={Boolean(busyId)}
              onClick={() => setPickTarget(null)}
            >
              Cancel
            </Button>
            <Link href="/admin/events/picks">
              <Button size="sm" variant="secondary" disabled={Boolean(busyId)}>
                Manage picks
              </Button>
            </Link>
          </>
        }
      >
        {pickTarget ? (
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              disabled={Boolean(busyId)}
              onClick={() => void addPadeyaPick(pickTarget, 1)}
            >
              Replace Primary
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={Boolean(busyId)}
              onClick={() => void addPadeyaPick(pickTarget, 2)}
            >
              Replace Secondary
            </Button>
          </div>
        ) : null}
      </Modal>
    </DashboardShell>
  );
}
