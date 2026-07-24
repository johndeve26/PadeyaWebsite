"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { AudienceMessageButton } from "@/components/messaging/AudienceMessageButton";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  EmptyState,
  Input,
  SectionHeader,
  Select,
  StatCard,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import {
  createSegment,
  deleteSegment,
  fetchAudienceMembers,
  fetchAudienceStats,
  fetchSegments,
} from "@/lib/crm-api";
import { fetchMyEvents, fetchTicketTypes } from "@/lib/events-api";
import { formatDateTime } from "@/lib/format";
import type {
  AudienceMember,
  AudienceSegment,
  AudienceStats,
} from "@/lib/types/crm";
import type { EventItem, TicketType } from "@/lib/types/events";

const STAT_LABELS: { key: keyof AudienceStats; label: string }[] = [
  { key: "followers", label: "Followers" },
  { key: "past_buyers", label: "Past buyers" },
  { key: "repeat_buyers", label: "Repeat buyers" },
  { key: "vip_buyers", label: "VIP buyers" },
  { key: "checked_in_attendees", label: "Checked in" },
  { key: "no_shows", label: "No-shows" },
  { key: "promo_code_buyers", label: "Promo buyers" },
  { key: "ambassador_referrals", label: "Referrals" },
  { key: "marketing_opted_in", label: "Marketing opt-in" },
];

type EventStatusFilter = "all" | "published" | "completed" | "other";
type MarketingFilter = "all" | "opted_in" | "opted_out";
type MemberSort = "name" | "tickets" | "recent";

function eventMatchesStatus(event: EventItem, filter: EventStatusFilter) {
  const status = (event.status || "").toLowerCase();
  if (filter === "all") return true;
  if (filter === "published") return status === "published" || status === "paused";
  if (filter === "completed") return status === "completed";
  return !["published", "paused", "completed"].includes(status);
}

export default function HostAudiencePage() {
  const toast = useToast();
  const [stats, setStats] = useState<AudienceStats | null>(null);
  const [segments, setSegments] = useState<AudienceSegment[]>([]);
  const [members, setMembers] = useState<AudienceMember[]>([]);
  const [membersLoading, setMembersLoading] = useState(true);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [ticketTypes, setTicketTypes] = useState<TicketType[]>([]);
  const [segmentKey, setSegmentKey] = useState("past_buyers");
  const [customSegmentId, setCustomSegmentId] = useState("");
  const [eventId, setEventId] = useState("");
  const [eventStatusFilter, setEventStatusFilter] =
    useState<EventStatusFilter>("published");
  const [ticketTypeId, setTicketTypeId] = useState("");
  const [checkInStatus, setCheckInStatus] = useState("");
  const [customName, setCustomName] = useState("");
  const [query, setQuery] = useState("");
  const [marketingFilter, setMarketingFilter] =
    useState<MarketingFilter>("all");
  const [sortKey, setSortKey] = useState<MemberSort>("recent");
  const [error, setError] = useState<string | null>(null);

  const systemSegments = useMemo(
    () => segments.filter((s) => s.is_system),
    [segments],
  );
  const customSegments = useMemo(
    () => segments.filter((s) => !s.is_system),
    [segments],
  );

  const filteredEvents = useMemo(
    () => events.filter((ev) => eventMatchesStatus(ev, eventStatusFilter)),
    [events, eventStatusFilter],
  );

  // Derive selection when the status filter drops the chosen event (avoid setState-in-effect).
  const resolvedEventId = useMemo(() => {
    if (!eventId) return "";
    return filteredEvents.some((ev) => ev.id === eventId) ? eventId : "";
  }, [eventId, filteredEvents]);
  const resolvedTicketTypeId = resolvedEventId ? ticketTypeId : "";
  const visibleTicketTypes = resolvedEventId ? ticketTypes : [];

  async function loadDashboard() {
    const [s, segs, evs] = await Promise.all([
      fetchAudienceStats(),
      fetchSegments(),
      fetchMyEvents(),
    ]);
    setStats(s);
    setSegments(segs);
    setEvents(evs);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await loadDashboard();
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load audience",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      setMembersLoading(true);
      try {
        const rows = await fetchAudienceMembers({
          segment_key: customSegmentId ? undefined : segmentKey,
          segment_id: customSegmentId || undefined,
          event_id: resolvedEventId || undefined,
          ticket_type_id: resolvedTicketTypeId || undefined,
          check_in_status: checkInStatus || undefined,
        });
        if (active) setMembers(rows);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load members",
          );
        }
      } finally {
        if (active) setMembersLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [
    segmentKey,
    customSegmentId,
    resolvedEventId,
    resolvedTicketTypeId,
    checkInStatus,
  ]);

  useEffect(() => {
    if (!resolvedEventId) return;
    let active = true;
    void fetchTicketTypes(resolvedEventId)
      .then((rows) => {
        if (active) setTicketTypes(rows);
      })
      .catch(() => {
        if (active) setTicketTypes([]);
      });
    return () => {
      active = false;
    };
  }, [resolvedEventId]);

  const visibleMembers = useMemo(() => {
    const q = query.trim().toLowerCase();
    let rows = members.filter((m) => {
      if (marketingFilter === "opted_in" && !m.marketing_opt_in) return false;
      if (marketingFilter === "opted_out" && m.marketing_opt_in) return false;
      if (!q) return true;
      return (
        m.display_name.toLowerCase().includes(q) ||
        m.email.toLowerCase().includes(q)
      );
    });
    rows = [...rows].sort((a, b) => {
      if (sortKey === "name") {
        return a.display_name.localeCompare(b.display_name);
      }
      if (sortKey === "tickets") {
        return b.tickets_purchased - a.tickets_purchased;
      }
      const aTime = a.last_order_at ? new Date(a.last_order_at).getTime() : 0;
      const bTime = b.last_order_at ? new Date(b.last_order_at).getTime() : 0;
      return bTime - aTime;
    });
    return rows;
  }, [members, query, marketingFilter, sortKey]);

  function selectSystemSegment(key: string) {
    setCustomSegmentId("");
    setSegmentKey(key);
    if (key === "checked_in_attendees") setCheckInStatus("checked_in");
    else if (key === "no_shows") setCheckInStatus("not_checked_in");
  }

  function selectCustomSegment(segment: AudienceSegment) {
    setCustomSegmentId(segment.id);
    setSegmentKey(segment.segment_key);
    const filters = segment.filters || {};
    setEventId(typeof filters.event_id === "string" ? filters.event_id : "");
    setTicketTypeId(
      typeof filters.ticket_type_id === "string" ? filters.ticket_type_id : "",
    );
    setCheckInStatus(
      typeof filters.check_in_status === "string"
        ? filters.check_in_status
        : "",
    );
  }

  function clearFilters() {
    setCustomSegmentId("");
    setSegmentKey("past_buyers");
    setEventId("");
    setTicketTypeId("");
    setCheckInStatus("");
    setEventStatusFilter("published");
    setQuery("");
    setMarketingFilter("all");
    setSortKey("recent");
  }

  async function onCreateSegment() {
    if (!customName.trim()) return;
    setError(null);
    try {
      const created = await createSegment({
        name: customName.trim(),
        segment_key: segmentKey,
        filters: {
          ...(resolvedEventId ? { event_id: resolvedEventId } : {}),
          ...(resolvedTicketTypeId
            ? { ticket_type_id: resolvedTicketTypeId }
            : {}),
          ...(checkInStatus ? { check_in_status: checkInStatus } : {}),
        },
      });
      setCustomName("");
      await loadDashboard();
      selectCustomSegment(created);
      toast.push({ tone: "success", title: "Segment saved" });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create segment");
    }
  }

  async function onDeleteSegment(segment: AudienceSegment) {
    if (segment.is_system) return;
    setError(null);
    try {
      await deleteSegment(segment.id);
      if (customSegmentId === segment.id) setCustomSegmentId("");
      toast.push({ tone: "success", title: "Segment deleted" });
      await loadDashboard();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not delete segment");
      throw err;
    }
  }

  const activeCustom = customSegments.find((s) => s.id === customSegmentId);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        compact
        eyebrow="Grow"
        title="Audience CRM"
        description="Filter buyers and followers for outreach. Members come from tickets and follows — save reusable segments, don’t invent lists."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/host/followers">
              <Button size="sm" variant="secondary">
                Followers
              </Button>
            </Link>
            <Link href="/host/announcements">
              <Button size="sm" variant="secondary">
                Announcements
              </Button>
            </Link>
            <Link href="/host/announcements/new">
              <Button size="sm">New announcement</Button>
            </Link>
          </div>
        }
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {stats ? (
          <div className="grid w-full gap-3 grid-cols-2 md:grid-cols-3 xl:grid-cols-5">
            {STAT_LABELS.map(({ key, label }) => {
              const selected =
                key === "marketing_opted_in"
                  ? marketingFilter === "opted_in"
                  : !customSegmentId && segmentKey === key;
              return (
                <button
                  key={key}
                  type="button"
                  className="min-w-0 w-full text-left"
                  onClick={() => {
                    if (key === "marketing_opted_in") {
                      setMarketingFilter((prev) =>
                        prev === "opted_in" ? "all" : "opted_in",
                      );
                      return;
                    }
                    selectSystemSegment(key);
                  }}
                >
                  <StatCard
                    title={label}
                    value={stats[key]}
                    className={cn(
                      "h-full w-full transition-shadow",
                      selected && "ring-1 ring-accent/50",
                    )}
                  />
                </button>
              );
            })}
          </div>
        ) : null}

        <div className="grid w-full gap-6 xl:grid-cols-12 xl:items-start">
          <Card className="space-y-4 xl:col-span-5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <SectionHeader
                title="Filter audience"
                description="Narrow by segment, published events, ticket type, and check-in."
                className="pb-0"
              />
              <Button size="sm" variant="ghost" onClick={clearFilters}>
                Clear
              </Button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Select
                label="Segment"
                value={customSegmentId ? `__custom:${customSegmentId}` : segmentKey}
                onChange={(e) => {
                  const value = e.target.value;
                  if (value.startsWith("__custom:")) {
                    const id = value.slice("__custom:".length);
                    const match = customSegments.find((s) => s.id === id);
                    if (match) selectCustomSegment(match);
                    return;
                  }
                  selectSystemSegment(value);
                }}
              >
                <optgroup label="System">
                  {systemSegments.map((s) => (
                    <option key={s.id} value={s.segment_key}>
                      {s.name} ({s.member_count})
                    </option>
                  ))}
                </optgroup>
                {customSegments.length ? (
                  <optgroup label="Custom">
                    {customSegments.map((s) => (
                      <option key={s.id} value={`__custom:${s.id}`}>
                        {s.name} ({s.member_count})
                      </option>
                    ))}
                  </optgroup>
                ) : null}
              </Select>

              <Select
                label="Event status"
                value={eventStatusFilter}
                onChange={(e) =>
                  setEventStatusFilter(e.target.value as EventStatusFilter)
                }
              >
                <option value="published">Published / live</option>
                <option value="completed">Completed</option>
                <option value="other">Drafts & other</option>
                <option value="all">All events</option>
              </Select>

              <Select
                label="Event"
                value={resolvedEventId}
                onChange={(e) => {
                  setEventId(e.target.value);
                  setTicketTypeId("");
                  setCustomSegmentId("");
                }}
              >
                <option value="">All events</option>
                {filteredEvents.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.title}
                  </option>
                ))}
              </Select>

              <Select
                label="Ticket type"
                value={resolvedTicketTypeId}
                onChange={(e) => {
                  setTicketTypeId(e.target.value);
                  setCustomSegmentId("");
                }}
                disabled={!resolvedEventId}
              >
                <option value="">Any</option>
                {visibleTicketTypes.map((tt) => (
                  <option key={tt.id} value={tt.id}>
                    {tt.name}
                  </option>
                ))}
              </Select>

              <Select
                label="Check-in status"
                value={checkInStatus}
                onChange={(e) => {
                  setCheckInStatus(e.target.value);
                  setCustomSegmentId("");
                }}
              >
                <option value="">Any</option>
                <option value="checked_in">Checked in</option>
                <option value="not_checked_in">Not checked in</option>
              </Select>

              <Select
                label="Marketing"
                value={marketingFilter}
                onChange={(e) =>
                  setMarketingFilter(e.target.value as MarketingFilter)
                }
              >
                <option value="all">Any</option>
                <option value="opted_in">Opted in</option>
                <option value="opted_out">Opted out</option>
              </Select>
            </div>

            {activeCustom ? (
              <p className="rounded-[var(--radius-md)] bg-muted px-3 py-2 text-xs text-muted-foreground">
                Using custom segment{" "}
                <span className="font-semibold text-foreground">
                  {activeCustom.name}
                </span>
                . Changing filters clears the custom selection.
              </p>
            ) : null}

            <div className="flex flex-wrap items-end gap-3 border-t border-border pt-4">
              <div className="min-w-[200px] flex-1">
                <Input
                  label="Save as custom segment"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder="e.g. Lagos VIP no-shows"
                  hint="Stores the current segment + filters."
                />
              </div>
              <Button
                type="button"
                variant="secondary"
                onClick={() => void onCreateSegment()}
              >
                Save segment
              </Button>
            </div>

            {customSegments.length ? (
              <div className="space-y-2 border-t border-border pt-4">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                  Custom segments
                </p>
                <ul className="divide-y divide-border rounded-[var(--radius-md)] border border-border">
                  {customSegments.map((s) => {
                    const selected = customSegmentId === s.id;
                    return (
                      <li
                        key={s.id}
                        className={cn(
                          "flex items-center justify-between gap-3 px-3 py-2 text-sm",
                          selected && "bg-muted/60",
                        )}
                      >
                        <button
                          type="button"
                          className="min-w-0 flex-1 text-left"
                          onClick={() => selectCustomSegment(s)}
                        >
                          <p className="truncate font-semibold text-foreground">
                            {s.name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {s.segment_key} · {s.member_count} members
                          </p>
                        </button>
                        <ConfirmAction
                          label="Delete"
                          title={`Delete segment “${s.name}”?`}
                          description="Custom segments are removed permanently. Member purchase history is unaffected."
                          confirmLabel="Delete segment"
                          tone="danger"
                          variant="ghost"
                          onConfirm={() => onDeleteSegment(s)}
                        />
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : null}
          </Card>

          <Card className="min-w-0 space-y-4 xl:col-span-7">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <SectionHeader
                title={`Members (${visibleMembers.length})`}
                description="Host ops only — emails stay in this workspace."
                className="pb-0"
              />
              <Badge tone="outline">Host ops only</Badge>
            </div>

            <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
              <Input
                label="Search members"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Name or email"
              />
              <Select
                label="Sort"
                value={sortKey}
                onChange={(e) => setSortKey(e.target.value as MemberSort)}
              >
                <option value="recent">Recent order</option>
                <option value="name">Name</option>
                <option value="tickets">Most tickets</option>
              </Select>
            </div>

            {membersLoading ? (
              <p className="text-sm text-muted-foreground">Loading members…</p>
            ) : visibleMembers.length === 0 ? (
              <EmptyState
                title="No members in this view"
                description="Try another segment, clear filters, or widen event status."
                action={
                  <Button size="sm" variant="secondary" onClick={clearFilters}>
                    Clear filters
                  </Button>
                }
              />
            ) : (
              <ul className="m-0 divide-y divide-border rounded-[var(--radius-md)] border border-border p-0">
                {visibleMembers.map((m) => (
                  <li
                    key={m.user_id}
                    className="flex flex-wrap items-center justify-between gap-3 px-4 py-3.5"
                  >
                    <div className="min-w-0 space-y-1">
                      <p className="font-bold text-foreground">
                        {m.display_name}
                      </p>
                      <p className="truncate text-sm text-muted-foreground">
                        {m.email}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {m.tickets_purchased} tickets · {m.events_attended}{" "}
                        events
                        {m.last_order_at
                          ? ` · Last order ${formatDateTime(m.last_order_at)}`
                          : ""}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {m.marketing_opt_in ? (
                        <Badge tone="accent" size="sm">
                          Opted in
                        </Badge>
                      ) : (
                        <Badge tone="neutral" size="sm">
                          Opted out
                        </Badge>
                      )}
                      <AudienceMessageButton
                        fanUserId={m.user_id}
                        fanName={m.display_name}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
