"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  SectionHeader,
  Select,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { fetchMyEvents } from "@/lib/events-api";
import { formatNgn } from "@/lib/format";
import {
  archiveHostShippingZone,
  createHostShippingZone,
  fetchHostShippingZones,
  updateHostShippingZone,
  type MerchShippingZone,
} from "@/lib/merch-api";
import type { EventItem } from "@/lib/types/events";

type ZoneFilter = "active" | "inactive" | "archived" | "all";

const ZONE_FILTERS: { value: ZoneFilter; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "archived", label: "Archived" },
  { value: "all", label: "All" },
];

function locationLabel(row: MerchShippingZone) {
  return [row.city, row.state, row.country].filter(Boolean).join(", ");
}

function zoneMatchesFilter(row: MerchShippingZone, filter: ZoneFilter) {
  if (filter === "all") return true;
  return (row.status || "").toLowerCase() === filter;
}

function emptyCopy(filter: ZoneFilter): { title: string; description: string } {
  switch (filter) {
    case "active":
      return {
        title: "No active zones",
        description:
          "Create a zone or activate an inactive one so checkout can charge delivery.",
      };
    case "inactive":
      return {
        title: "No inactive zones",
        description: "Deactivated zones appear here and stay out of checkout.",
      };
    case "archived":
      return {
        title: "No archived zones",
        description: "Archived zones keep history without affecting new orders.",
      };
    default:
      return {
        title: "No shipping zones yet",
        description:
          "Add a Lagos or Nigeria zone so shipping checkout can charge a flat fee.",
      };
  }
}

export default function HostMerchShippingZonesPage() {
  const [rows, setRows] = useState<MerchShippingZone[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [name, setName] = useState("");
  const [country, setCountry] = useState("Nigeria");
  const [state, setState] = useState("Lagos");
  const [city, setCity] = useState("");
  const [flatFee, setFlatFee] = useState("2000");
  const [eventId, setEventId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [filter, setFilter] = useState<ZoneFilter>("active");
  const [loading, setLoading] = useState(true);

  async function load() {
    const [zoneRows, eventRows] = await Promise.all([
      fetchHostShippingZones(),
      fetchMyEvents(),
    ]);
    setRows(zoneRows);
    setEvents(eventRows);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.detail
              : "Failed to load shipping zones",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const counts = useMemo(() => {
    const next: Record<ZoneFilter, number> = {
      active: 0,
      inactive: 0,
      archived: 0,
      all: rows.length,
    };
    for (const row of rows) {
      const status = (row.status || "").toLowerCase();
      if (status === "active") next.active += 1;
      else if (status === "inactive") next.inactive += 1;
      else if (status === "archived") next.archived += 1;
    }
    return next;
  }, [rows]);

  const visible = useMemo(
    () => rows.filter((row) => zoneMatchesFilter(row, filter)),
    [rows, filter],
  );

  const eventTitle = (id: string | null | undefined) => {
    if (!id) return "All host events";
    return events.find((e) => e.id === id)?.title || "Event-scoped";
  };

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await createHostShippingZone({
        name: name.trim(),
        country: country.trim(),
        state: state.trim() || null,
        city: city.trim() || null,
        flat_fee: Number(flatFee || 0),
        event_id: eventId || null,
      });
      setName("");
      setCity("");
      setFilter("active");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Create failed");
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(row: MerchShippingZone) {
    if (row.status === "archived") return;
    try {
      await updateHostShippingZone(row.id, {
        status: row.status === "active" ? "inactive" : "active",
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    }
  }

  async function onArchive(row: MerchShippingZone) {
    try {
      await archiveHostShippingZone(row.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Archive failed");
    }
  }

  const empty = emptyCopy(filter);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        compact
        eyebrow="Merch Studio"
        title="Shipping zones"
        description="Flat delivery fees for Pàdéyá merch checkout. Most specific match wins — country, then state, then city."
        actions={
          <Link href="/host/merchandise">
            <Button size="sm" variant="secondary">
              Back to merch
            </Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        <div className="grid w-full gap-6 xl:grid-cols-12 xl:items-start">
          <Card className="space-y-4 xl:col-span-5">
            <SectionHeader
              title="Create shipping zone"
              description="Match by country, then optional state and city."
            />
            <form className="space-y-4" onSubmit={onCreate}>
              <Input
                label="Zone name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Lagos delivery"
                required
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  label="Country"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  required
                />
                <Input
                  label="State"
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  placeholder="Lagos"
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  label="City"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="Optional — whole state if blank"
                />
                <Input
                  label="Flat fee (₦)"
                  type="number"
                  min={0}
                  step="1"
                  value={flatFee}
                  onChange={(e) => setFlatFee(e.target.value)}
                  required
                />
              </div>
              <Select
                label="Event scope"
                value={eventId}
                onChange={(e) => setEventId(e.target.value)}
              >
                <option value="">All host events</option>
                {events.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.title}
                  </option>
                ))}
              </Select>
              <p className="text-xs text-muted-foreground">
                Carrier labels and delivery estimates are not available yet —
                fulfillment stays manual on the order queue.
              </p>
              <Button type="submit" disabled={saving} className="w-full sm:w-auto">
                {saving ? "Saving…" : "Create zone"}
              </Button>
            </form>
          </Card>

          <Card className="min-w-0 space-y-4 xl:col-span-7">
            <SectionHeader
              title="Your zones"
              description="Only active zones apply at checkout. Inactive and archived keep history."
            />

            <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
              <div
                role="tablist"
                aria-label="Shipping zone filters"
                className="flex min-w-0 flex-1 gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
              >
                {ZONE_FILTERS.map((tab) => {
                  const selected = filter === tab.value;
                  return (
                    <button
                      key={tab.value}
                      type="button"
                      role="tab"
                      aria-selected={selected}
                      onClick={() => setFilter(tab.value)}
                      className={cn(
                        "inline-flex shrink-0 items-center gap-1.5 rounded-[calc(var(--radius-md)-2px)] px-3 py-2 text-sm font-semibold transition-colors",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                        selected
                          ? "bg-muted text-foreground ring-1 ring-border"
                          : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
                      )}
                    >
                      {tab.label}
                      <span
                        className={cn(
                          "rounded-full px-1.5 py-0.5 text-[10px] font-bold tabular-nums",
                          selected
                            ? "bg-surface-elevated text-foreground"
                            : "bg-muted text-muted-foreground",
                        )}
                      >
                        {counts[tab.value]}
                      </span>
                    </button>
                  );
                })}
              </div>
              <p className="shrink-0 text-xs font-semibold tabular-nums text-muted-foreground">
                {visible.length} of {rows.length}
              </p>
            </div>

            {loading ? (
              <p className="text-sm text-muted-foreground">Loading zones…</p>
            ) : visible.length === 0 ? (
              <EmptyState
                title={empty.title}
                description={empty.description}
              />
            ) : (
              <ul className="m-0 divide-y divide-border rounded-[var(--radius-md)] border border-border p-0">
                {visible.map((row) => (
                  <li
                    key={row.id}
                    className="flex flex-wrap items-center justify-between gap-3 px-4 py-4 sm:gap-4"
                  >
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-foreground">
                          {row.name}
                        </p>
                        <Badge
                          tone={
                            row.status === "active"
                              ? "success"
                              : row.status === "archived"
                                ? "neutral"
                                : "warning"
                          }
                          size="sm"
                        >
                          {row.status}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {locationLabel(row)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {eventTitle(row.event_id)}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-2 sm:flex-row sm:items-center">
                      <p className="text-base font-extrabold tabular-nums text-foreground">
                        {formatNgn(row.flat_fee)}
                      </p>
                      <div className="flex flex-wrap justify-end gap-2">
                        {row.status !== "archived" ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => void toggleActive(row)}
                          >
                            {row.status === "active"
                              ? "Deactivate"
                              : "Activate"}
                          </Button>
                        ) : null}
                        {row.status !== "archived" ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => void onArchive(row)}
                          >
                            Archive
                          </Button>
                        ) : null}
                      </div>
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
