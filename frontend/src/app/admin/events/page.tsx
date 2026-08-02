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
  clearEventFlag,
  fetchAdminEvents,
  flagEvent,
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
];

const FLAG_OPTIONS = [
  { value: "all", label: "Any flag" },
  { value: "flagged", label: "Flagged only" },
  { value: "clear", label: "Not flagged" },
];

type PickSlotInfo = { slot_number: number; slot_label: string };

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

  const flaggedCount =
    events?.filter((e) => e.admin_flagged || e.admin_flagged_at).length ?? 0;
  const pickCount = Object.keys(pickByEventId).length;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="All events"
      description="Review any listing, flag for follow-up, manage featured placement, and choose Pàdéyá Picks."
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
                  return (
                    <div className="flex flex-wrap gap-2">
                      <Link href={`/admin/events/${e.id}/review`}>
                        <Button size="sm" variant="secondary">
                          Review
                        </Button>
                      </Link>
                      {isFlagged ? (
                        <ConfirmAction
                          label="Clear flag"
                          title="Clear admin flag?"
                          description={`Remove the ops flag from “${e.title}”.`}
                          confirmLabel="Clear flag"
                          size="sm"
                          busy={busyId === e.id}
                          onConfirm={() => onClearFlag(e)}
                        />
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={busyId === e.id}
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
                            busy={busyId === e.id}
                            onConfirm={() => removePadeyaPick(e)}
                          />
                        ) : (
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={busyId === e.id}
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
                            busy={busyId === e.id}
                            onConfirm={() => toggleFeatured(e)}
                          />
                        ) : (
                          <ConfirmAction
                            label="Feature"
                            title="Feature this event?"
                            description={`"${e.title}" will appear in featured listings on the platform.`}
                            confirmLabel="Feature"
                            busy={busyId === e.id}
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
