"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { HostEventListCard } from "@/components/host/HostEventListCard";
import {
  HostEventsListView,
  HostEventsTable,
  HostEventsToolbar,
  useHostEventListMetrics,
  VIEW_MODE_STORAGE_KEY,
} from "@/components/host/events/HostEventsViews";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  EmptyState,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { cancelEvent, discardEvent, fetchMyEvents } from "@/lib/events-api";
import {
  canEditEvents,
  canScanMerch,
  canScanTickets,
  hasHostPermission,
  isDeskFocusedStaff,
  isMerchOnlyStaff,
  isScannerOnlyStaff,
} from "@/lib/host-access";
import {
  emptyStateForTab,
  EVENT_LIST_TABS,
  filterEventsForList,
  parseEventListTab,
  sortEventsForList,
  uniqueEventCities,
  viewHref,
  type EventListTab,
  type EventSortKey,
  type EventViewMode,
} from "@/lib/host-events-list";
import { fetchWorkspaceDeskEvents } from "@/lib/hosts-api";
import type { EventItem, EventStatus } from "@/lib/types/events";

function canDiscard(event: EventItem): boolean {
  return event.status === "draft" || event.status === "rejected";
}

function canCancel(event: EventItem): boolean {
  return ["draft", "rejected", "pending_review", "published", "paused"].includes(
    event.status,
  );
}

function readStoredViewMode(): EventViewMode {
  if (typeof window === "undefined") return "table";
  const stored = window.localStorage.getItem(VIEW_MODE_STORAGE_KEY);
  if (stored === "table" || stored === "list" || stored === "grid") return stored;
  return "table";
}

export default function HostEventsPage() {
  const toast = useToast();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { active, isOwner } = useHostWorkspace();

  const deskOnly = Boolean(active && isDeskFocusedStaff(active));
  const scannerOnly = Boolean(active && isScannerOnlyStaff(active));
  const merchOnly = Boolean(active && isMerchOnlyStaff(active));

  const allowMutate = isOwner || canEditEvents(active);
  const allowCheckIn = isOwner || canScanTickets(active);
  const allowMerch =
    isOwner ||
    hasHostPermission(
      active,
      "merch.view",
      "merch.create",
      "merch.edit",
    ) ||
    canScanMerch(active);
  const allowAmbassadors =
    isOwner ||
    hasHostPermission(active, "ambassadors.view", "events.edit");
  const allowAnalytics =
    isOwner ||
    hasHostPermission(
      active,
      "analytics.view_events",
      "analytics.view_merch",
      "analytics.view_sponsors",
    );
  const showFinance =
    isOwner ||
    hasHostPermission(active, "finance.view_sales_summary");
  const showOpsMetrics =
    !scannerOnly &&
    !merchOnly &&
    (allowAnalytics || showFinance || allowMerch);

  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [deskEventIds, setDeskEventIds] = useState<Set<string> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<EventStatus | "all">("all");
  const [cityFilter, setCityFilter] = useState("all");
  const [visibilityFilter, setVisibilityFilter] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sortKey, setSortKey] = useState<EventSortKey>("start_asc");
  const [viewMode, setViewMode] = useState<EventViewMode>(() => readStoredViewMode());
  const [listNowMs] = useState(() => Date.now());
  const tab = parseEventListTab(searchParams.get("tab"));

  // Desk staff: never render the studio grid path (localStorage may still say "grid").
  // Table/list reuse HostEventRowActions; grid cards are also desk-safe if reached.
  const effectiveViewMode: EventViewMode =
    deskOnly && viewMode === "grid" ? "table" : viewMode;

  useEffect(() => {
    void fetchMyEvents()
      .then(setEvents)
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load");
        setEvents([]);
      });
  }, []);

  useEffect(() => {
    if (!active?.host_id || !deskOnly) return;
    let cancelled = false;
    void fetchWorkspaceDeskEvents(active.host_id)
      .then((rows) => {
        if (!cancelled) setDeskEventIds(new Set(rows.map((row) => row.id)));
      })
      .catch(() => {
        if (!cancelled) setDeskEventIds(new Set());
      });
    return () => {
      cancelled = true;
    };
  }, [active?.host_id, deskOnly]);

  const loaded = useMemo(() => {
    const rows = events ?? [];
    if (!deskOnly) return rows;
    if (deskEventIds == null) return [];
    return rows.filter((event) => deskEventIds.has(event.id));
  }, [events, deskOnly, deskEventIds]);

  const cities = useMemo(() => uniqueEventCities(loaded), [loaded]);

  const tabCounts = useMemo(() => {
    const counts: Record<EventListTab, number> = {
      upcoming: 0,
      drafts: 0,
      published: 0,
      past: 0,
      cancelled: 0,
      all: loaded.length,
    };
    for (const event of loaded) {
      for (const t of EVENT_LIST_TABS) {
        if (t.value === "all") continue;
        if (
          filterEventsForList([event], {
            tab: t.value,
            query: "",
            statusFilter: "all",
            cityFilter: "all",
            visibilityFilter: "all",
            nowMs: listNowMs,
          }).length
        ) {
          counts[t.value] += 1;
        }
      }
    }
    return counts;
  }, [loaded, listNowMs]);

  const preSortFiltered = useMemo(() => {
    return filterEventsForList(loaded, {
      tab,
      query,
      statusFilter,
      cityFilter,
      visibilityFilter,
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
    });
  }, [
    loaded,
    tab,
    query,
    statusFilter,
    cityFilter,
    visibilityFilter,
    dateFrom,
    dateTo,
  ]);

  const { metrics, loading: metricsLoading } = useHostEventListMetrics({
    eventIds: preSortFiltered.map((event) => event.id),
    loadAnalytics: showOpsMetrics,
    loadMerch: showOpsMetrics && allowMerch,
    showFinance,
  });

  const filtered = useMemo(() => {
    return sortEventsForList(preSortFiltered, sortKey, metrics);
  }, [preSortFiltered, sortKey, metrics]);

  const rowActions = useMemo(
    () => ({
      canView: isOwner || hasHostPermission(active, "events.view"),
      canEdit: allowMutate && !scannerOnly && !merchOnly,
      canTickets: allowMutate && !scannerOnly && !merchOnly,
      canScanner: allowCheckIn && !merchOnly,
      canMerch: allowMerch && !scannerOnly,
      canAmbassadors: allowAmbassadors && !scannerOnly && !merchOnly,
      canAnalytics: allowAnalytics && !scannerOnly && !merchOnly,
      showFinance,
      showOpsMetrics,
      scannerOnly,
      merchOnly,
      deskOnly,
    }),
    [
      active,
      allowMutate,
      allowCheckIn,
      allowMerch,
      allowAmbassadors,
      allowAnalytics,
      showFinance,
      showOpsMetrics,
      scannerOnly,
      merchOnly,
      deskOnly,
      isOwner,
    ],
  );

  function setTab(next: EventListTab) {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "upcoming") params.delete("tab");
    else params.set("tab", next);
    const qs = params.toString();
    router.replace(qs ? `/host/events?${qs}` : "/host/events");
  }

  function persistViewMode(mode: EventViewMode) {
    setViewMode(mode);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode);
    }
  }

  function openView(event: EventItem) {
    window.open(viewHref(event), "_blank", "noopener,noreferrer");
  }

  async function onDelete(event: EventItem) {
    setError(null);
    try {
      if (canDiscard(event)) {
        await discardEvent(event.id);
        setEvents((prev) => (prev ?? []).filter((e) => e.id !== event.id));
        toast.push({ tone: "success", title: "Event deleted" });
        return;
      }
      if (canCancel(event)) {
        const updated = await cancelEvent(event.id);
        setEvents((prev) =>
          (prev ?? []).map((e) => (e.id === updated.id ? updated : e)),
        );
        toast.push({
          tone: "success",
          title: "Event cancelled",
          description: "Listings with sales are cancelled, not hard-deleted.",
        });
        return;
      }
      throw new Error("This event cannot be deleted from its current status.");
    } catch (err) {
      const detail =
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Delete failed";
      setError(detail);
      toast.push({
        tone: "danger",
        title: "Could not delete event",
        description: detail,
      });
      throw err;
    }
  }

  const emptyCopy = emptyStateForTab(tab);
  const pageDescription = scannerOnly
    ? "Assigned events for door scanning."
    : merchOnly
      ? "Assigned events for merch and pickup."
      : deskOnly
        ? "Assigned events — scanner and pickup shortcuts."
        : allowMutate
          ? "Search, filter, and run your event portfolio."
          : "Events visible for your role.";

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        operationalHeader
        title="Events"
        description={pageDescription}
        actions={
          allowMutate && !deskOnly ? (
            <div className="flex flex-wrap items-center gap-2">
              <Link href="/host/analytics">
                <Button variant="secondary">Portfolio analytics</Button>
              </Link>
              <Link href="/host/events/new">
                <Button>Create event</Button>
              </Link>
            </div>
          ) : deskOnly ? (
            <Link href="/host/desk">
              <Button>Open desk</Button>
            </Link>
          ) : (
            <Badge tone="neutral">View only</Badge>
          )
        }
      >
        {error ? (
          <Alert tone="danger" title="Unable to load events">
            {error}
          </Alert>
        ) : null}

        {loaded.length > 0 ? (
          <HostEventsToolbar
            tab={tab}
            tabCounts={tabCounts}
            onTabChange={setTab}
            query={query}
            onQueryChange={setQuery}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            cityFilter={cityFilter}
            onCityFilterChange={setCityFilter}
            cities={cities}
            visibilityFilter={visibilityFilter}
            onVisibilityFilterChange={setVisibilityFilter}
            dateFrom={dateFrom}
            onDateFromChange={setDateFrom}
            dateTo={dateTo}
            onDateToChange={setDateTo}
            sortKey={sortKey}
            onSortKeyChange={setSortKey}
            showOpsMetrics={showOpsMetrics}
            showFinance={showFinance}
            viewMode={effectiveViewMode}
            onViewModeChange={persistViewMode}
            allowGridView={!deskOnly}
            filteredCount={filtered.length}
            totalCount={loaded.length}
          />
        ) : null}

        <div className="space-y-5">
          {events === null && !error ? (
            <SkeletonLoader lines={6} />
          ) : deskOnly && deskEventIds == null && !error ? (
            <SkeletonLoader lines={4} />
          ) : loaded.length === 0 && !error ? (
            <EmptyState
              title={deskOnly ? "No assigned events yet" : "No events yet"}
              description={
                deskOnly
                  ? "Ask the host owner to assign you on an event or grant desk access."
                  : allowMutate
                    ? "Create your first event to start selling tickets."
                    : "No events are visible for your role yet."
              }
              action={
                allowMutate && !deskOnly ? (
                  <Link href="/host/events/new">
                    <Button size="lg">Create event</Button>
                  </Link>
                ) : deskOnly ? (
                  <Link href="/host/desk">
                    <Button size="lg">Open desk</Button>
                  </Link>
                ) : undefined
              }
            />
          ) : filtered.length === 0 ? (
            <EmptyState
              title={emptyCopy.title}
              description={emptyCopy.description}
              action={
                tab !== "upcoming" ? (
                  <Button variant="secondary" onClick={() => setTab("upcoming")}>
                    Show upcoming
                  </Button>
                ) : allowMutate && !deskOnly ? (
                  <Link href="/host/events/new">
                    <Button>Create event</Button>
                  </Link>
                ) : undefined
              }
            />
          ) : effectiveViewMode === "table" ? (
            <HostEventsTable
              events={filtered}
              actions={rowActions}
              metrics={metrics}
              metricsLoading={metricsLoading}
              onView={openView}
            />
          ) : effectiveViewMode === "list" ? (
            <HostEventsListView
              events={filtered}
              actions={rowActions}
              metrics={metrics}
              metricsLoading={metricsLoading}
              onView={openView}
            />
          ) : (
            filtered.map((event) => {
              // Owner/studio grid only — desk roles are coerced to table above.
              const studioMutate =
                allowMutate && !deskOnly && !scannerOnly && !merchOnly;
              const discardable = studioMutate && canDiscard(event);
              const deletable =
                studioMutate && (discardable || canCancel(event));
              return (
                <HostEventListCard
                  key={event.id}
                  event={event}
                  deletable={deletable}
                  discardable={discardable}
                  editable={studioMutate}
                  canCheckIn={allowCheckIn && !merchOnly && !deskOnly}
                  rowActions={rowActions}
                  onView={() => openView(event)}
                  onDelete={() => onDelete(event)}
                />
              );
            })
          )}
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
