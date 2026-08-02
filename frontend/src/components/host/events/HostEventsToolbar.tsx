"use client";

import { type ReactNode, useMemo, useState } from "react";

import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  EVENT_LIST_TABS,
  EVENT_VISIBILITY_OPTIONS,
  type EventListTab,
  type EventSortKey,
  type EventViewMode,
} from "@/lib/host-events-list";
import { fieldControlClass } from "@/lib/ui/field";
import type { EventStatus } from "@/lib/types/events";

const VIEW_MODES: { value: EventViewMode; label: string }[] = [
  { value: "table", label: "Table" },
  { value: "list", label: "List" },
  { value: "grid", label: "Grid" },
];

const filterControlClass = fieldControlClass({
  className: "h-10 px-3 text-sm",
});

const filterLabelClass =
  "sr-only text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground";

type HostEventsToolbarProps = {
  tab: EventListTab;
  tabCounts: Record<EventListTab, number>;
  onTabChange: (tab: EventListTab) => void;
  query: string;
  onQueryChange: (value: string) => void;
  statusFilter: EventStatus | "all";
  onStatusFilterChange: (value: EventStatus | "all") => void;
  cityFilter: string;
  onCityFilterChange: (value: string) => void;
  cities: string[];
  visibilityFilter: string;
  onVisibilityFilterChange: (value: string) => void;
  dateFrom: string;
  onDateFromChange: (value: string) => void;
  dateTo: string;
  onDateToChange: (value: string) => void;
  sortKey: EventSortKey;
  onSortKeyChange: (value: EventSortKey) => void;
  showOpsMetrics: boolean;
  showFinance: boolean;
  viewMode: EventViewMode;
  onViewModeChange: (mode: EventViewMode) => void;
  /** Desk-focused staff: hide Grid (table/list + row actions stay permission-safe). */
  allowGridView?: boolean;
  filteredCount: number;
  totalCount: number;
};

function FilterField({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={cn("block min-w-0", className)}>
      <span className={filterLabelClass}>{label}</span>
      {children}
    </label>
  );
}

export function HostEventsToolbar({
  tab,
  tabCounts,
  onTabChange,
  query,
  onQueryChange,
  statusFilter,
  onStatusFilterChange,
  cityFilter,
  onCityFilterChange,
  cities,
  visibilityFilter,
  onVisibilityFilterChange,
  dateFrom,
  onDateFromChange,
  dateTo,
  onDateToChange,
  sortKey,
  onSortKeyChange,
  showOpsMetrics,
  showFinance,
  viewMode,
  onViewModeChange,
  allowGridView = true,
  filteredCount,
  totalCount,
}: HostEventsToolbarProps) {
  const [filtersOpen, setFiltersOpen] = useState(false);
  const viewModes = useMemo(
    () =>
      allowGridView
        ? VIEW_MODES
        : VIEW_MODES.filter((mode) => mode.value !== "grid"),
    [allowGridView],
  );

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (statusFilter !== "all") count += 1;
    if (cityFilter !== "all") count += 1;
    if (visibilityFilter !== "all") count += 1;
    if (dateFrom) count += 1;
    if (dateTo) count += 1;
    if (sortKey !== "start_asc") count += 1;
    return count;
  }, [statusFilter, cityFilter, visibilityFilter, dateFrom, dateTo, sortKey]);

  return (
    <div className="min-w-0 space-y-3 rounded-[var(--radius-lg)] border border-border bg-card p-3 shadow-[var(--shadow-soft)] dark:bg-surface-elevated sm:p-4">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <div
          role="tablist"
          aria-label="Event list tabs"
          className="flex min-w-0 flex-1 gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          {EVENT_LIST_TABS.map((t) => {
            const selected = tab === t.value;
            return (
              <button
                key={t.value}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => onTabChange(t.value)}
                className={cn(
                  "inline-flex shrink-0 items-center gap-1.5 rounded-[calc(var(--radius-md)-2px)] px-3 py-2 text-sm font-semibold transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  selected
                    ? "bg-muted text-foreground ring-1 ring-border"
                    : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
                )}
              >
                {t.label}
                <span
                  className={cn(
                    "rounded-full px-1.5 py-0.5 text-[10px] font-bold tabular-nums",
                    selected
                      ? "bg-surface-elevated text-foreground"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {tabCounts[t.value]}
                </span>
              </button>
            );
          })}
        </div>
        <Badge tone="neutral" className="shrink-0">
          {filteredCount} of {totalCount}
        </Badge>
      </div>

      <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center">
        <div className="min-w-0 flex-1">
          <label className="block min-w-0">
            <span className={filterLabelClass}>Search events</span>
            <input
              type="search"
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              placeholder="Title, venue, city, slug…"
              className={fieldControlClass({
                className: "h-10 w-full px-3",
              })}
            />
          </label>
        </div>
        <div
          className="flex shrink-0 items-center gap-1 rounded-[var(--radius-md)] border border-border bg-muted p-1"
          role="group"
          aria-label="View mode"
        >
          {viewModes.map((mode) => (
            <button
              key={mode.value}
              type="button"
              onClick={() => onViewModeChange(mode.value)}
              aria-pressed={viewMode === mode.value}
              className={cn(
                "rounded-[calc(var(--radius-md)-2px)] px-3 py-1.5 text-xs font-bold uppercase tracking-[0.06em] transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                viewMode === mode.value
                  ? "bg-card text-foreground shadow-[var(--shadow-soft)] ring-1 ring-border dark:bg-surface-elevated"
                  : "text-muted-foreground hover:bg-surface-inset hover:text-foreground",
              )}
            >
              {mode.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex min-w-0 items-center gap-2 md:hidden">
        <button
          type="button"
          onClick={() => setFiltersOpen((open) => !open)}
          aria-expanded={filtersOpen}
          className={cn(
            filterControlClass,
            "inline-flex w-auto items-center gap-2 px-3 font-semibold",
          )}
        >
          Filters
          {activeFilterCount > 0 ? (
            <span className="rounded-full bg-ink px-1.5 py-0.5 text-[10px] font-bold text-paper">
              {activeFilterCount}
            </span>
          ) : null}
        </button>
      </div>

      <div
        className={cn(
          "flex min-w-0 flex-wrap items-end gap-2",
          !filtersOpen && "hidden md:flex",
        )}
      >
        <FilterField label="Status" className="w-full min-w-[8rem] sm:w-auto sm:min-w-[9rem]">
          <select
            value={statusFilter}
            onChange={(e) =>
              onStatusFilterChange(e.target.value as EventStatus | "all")
            }
            className={filterControlClass}
          >
            <option value="all">All statuses</option>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="paused">Paused</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
            <option value="rejected">Rejected</option>
          </select>
        </FilterField>

        <FilterField label="City" className="w-full min-w-[8rem] sm:w-auto sm:min-w-[9rem]">
          <select
            value={cityFilter}
            onChange={(e) => onCityFilterChange(e.target.value)}
            className={filterControlClass}
          >
            <option value="all">All cities</option>
            {cities.map((city) => (
              <option key={city} value={city}>
                {city}
              </option>
            ))}
          </select>
        </FilterField>

        <FilterField
          label="Visibility"
          className="w-full min-w-[8rem] sm:w-auto sm:min-w-[10rem]"
        >
          <select
            value={visibilityFilter}
            onChange={(e) => onVisibilityFilterChange(e.target.value)}
            className={filterControlClass}
          >
            <option value="all">All visibility</option>
            {EVENT_VISIBILITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </FilterField>

        <FilterField label="Start from" className="w-full min-w-[8rem] sm:w-auto">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => onDateFromChange(e.target.value)}
            className={filterControlClass}
          />
        </FilterField>

        <FilterField label="Start until" className="w-full min-w-[8rem] sm:w-auto">
          <input
            type="date"
            value={dateTo}
            onChange={(e) => onDateToChange(e.target.value)}
            className={filterControlClass}
          />
        </FilterField>

        <FilterField label="Sort" className="w-full min-w-[10rem] sm:w-auto sm:min-w-[12rem]">
          <select
            value={sortKey}
            onChange={(e) => onSortKeyChange(e.target.value as EventSortKey)}
            className={filterControlClass}
          >
            <option value="start_asc">Start date (soonest)</option>
            <option value="start_desc">Start date (latest)</option>
            <option value="created_desc">Recently created</option>
            {showOpsMetrics ? (
              <>
                <option value="sales_desc">Tickets sold</option>
                {showFinance ? (
                  <option value="revenue_desc">Revenue</option>
                ) : null}
              </>
            ) : null}
            <option value="title_asc">Title A–Z</option>
          </select>
        </FilterField>
      </div>
    </div>
  );
}
