"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { PlacementPreview } from "@/components/admin/PlacementPreview";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  Input,
  Select,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminEvents } from "@/lib/events-api";
import {
  fetchFeaturedPlacements,
  swapListingPadeyaPicks,
  upsertFeaturedPlacementSet,
  type FeaturedPlacementSlot,
} from "@/lib/placements-api";
import type { EventItem } from "@/lib/types/events";
type PickContext = "homepage" | "events_page";

function EventSlotPicker({
  label,
  events,
  value,
  excludeId,
  onChange,
}: {
  label: string;
  events: EventItem[];
  value: string;
  excludeId?: string;
  onChange: (id: string) => void;
}) {
  const [q, setQ] = useState("");
  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return events
      .filter((e) => e.id !== excludeId)
      .filter((e) => {
        if (!needle) return true;
        return (
          e.title.toLowerCase().includes(needle) ||
          (e.city || "").toLowerCase().includes(needle) ||
          (e.slug || "").toLowerCase().includes(needle)
        );
      })
      .slice(0, 50);
  }, [events, excludeId, q]);

  const selected = events.find((e) => e.id === value);

  return (
    <div className="space-y-2">
      <p className="text-sm font-semibold text-foreground">{label}</p>
      {selected ? (
        <p className="text-sm text-muted-foreground">
          Selected:{" "}
          <span className="font-semibold text-foreground">{selected.title}</span>
          {selected.city ? ` · ${selected.city}` : ""}
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">No listing selected</p>
      )}
      <Input
        label="Search published listings"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Title, city, or slug…"
      />
      <select
        className="h-11 w-full rounded-[var(--radius-md)] border border-input-border bg-input-background px-3 text-sm text-input-foreground"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Clear slot</option>
        {filtered.map((ev) => (
          <option key={ev.id} value={ev.id}>
            {ev.title}
            {ev.city ? ` · ${ev.city}` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function AdminListingPadeyaPicksPage() {
  const toast = useToast();
  const [context, setContext] = useState<PickContext>("homepage");
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [slots, setSlots] = useState<FeaturedPlacementSlot[] | null>(null);
  const [slot1, setSlot1] = useState("");
  const [slot2, setSlot2] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const published = useMemo(
    () =>
      (events ?? []).filter(
        (e) =>
          e.status === "published" &&
          (e.visibility === "listed" ||
            e.visibility === "approval_required" ||
            !e.visibility),
      ),
    [events],
  );

  const load = useCallback(async () => {
    const [allEvents, placementSlots] = await Promise.all([
      fetchAdminEvents(),
      fetchFeaturedPlacements({ context_type: context }),
    ]);
    setEvents(allEvents);
    setSlots(placementSlots);
    const primary = placementSlots.find((s) => s.slot_number === 1);
    const secondary = placementSlots.find((s) => s.slot_number === 2);
    setSlot1(primary?.event_id || "");
    setSlot2(secondary?.event_id || "");
  }, [context]);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        await load();
        if (alive) setError(null);
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load Pàdéyá Picks",
          );
          setEvents([]);
          setSlots([]);
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, [load]);

  const previewEvents = useMemo(() => {
    const byId = new Map(published.map((e) => [e.id, e]));
    return [slot1, slot2]
      .map((id) => (id ? byId.get(id) : null))
      .filter((e): e is EventItem => Boolean(e));
  }, [published, slot1, slot2]);

  async function saveSlots() {
    setBusy(true);
    setError(null);
    try {
      await upsertFeaturedPlacementSet({
        context_type: context,
        slot_1: { event_id: slot1 || null },
        slot_2: { event_id: slot2 || null },
        status: slot1 || slot2 ? "active" : "draft",
      });
      await load();
      toast.push({ tone: "success", title: "Pàdéyá Picks updated" });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to save Pàdéyá Picks",
      );
    } finally {
      setBusy(false);
    }
  }

  async function onSwap() {
    setBusy(true);
    setError(null);
    try {
      await swapListingPadeyaPicks({ context_type: context });
      await load();
      toast.push({ tone: "success", title: "Primary and Secondary swapped" });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Swap failed");
    } finally {
      setBusy(false);
    }
  }

  const dirty =
    (slots?.find((s) => s.slot_number === 1)?.event_id || "") !== slot1 ||
    (slots?.find((s) => s.slot_number === 2)?.event_id || "") !== slot2;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Listings"
      title="Pàdéyá Picks"
      description="Choose which published listings appear as Primary and Secondary Spotlights. Public discovery only shows live, published picks."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/events">
            <Button variant="secondary">All listings</Button>
          </Link>
          <Link href="/admin/featured-placements">
            <Button variant="ghost">All placement contexts</Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Pàdéyá Picks">
          {error}
        </Alert>
      ) : null}

      {events == null || slots == null ? (
        <SkeletonLoader lines={5} />
      ) : (
        <div className="space-y-6">
          <Card className="space-y-4 p-5">
            <Select
              label="Surface"
              value={context}
              onChange={(e) => setContext(e.target.value as PickContext)}
            >
              <option value="homepage">Homepage Pàdéyá Picks</option>
              <option value="events_page">Events page Pàdéyá Picks</option>
            </Select>
            <p className="text-sm text-muted-foreground">
              City, category, and other hub picks stay under{" "}
              <Link
                href="/admin/featured-placements"
                className="font-semibold text-primary underline-offset-2 hover:underline"
              >
                Featured Placement Slots
              </Link>
              .
            </p>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="space-y-4 p-5">
              <div className="flex items-center gap-2">
                <Badge tone="accent">Primary</Badge>
                <span className="text-sm text-muted-foreground">Slot 1</span>
              </div>
              <EventSlotPicker
                label="Primary Spotlight listing"
                events={published}
                value={slot1}
                excludeId={slot2 || undefined}
                onChange={setSlot1}
              />
            </Card>
            <Card className="space-y-4 p-5">
              <div className="flex items-center gap-2">
                <Badge tone="neutral">Secondary</Badge>
                <span className="text-sm text-muted-foreground">Slot 2</span>
              </div>
              <EventSlotPicker
                label="Secondary Spotlight listing"
                events={published}
                value={slot2}
                excludeId={slot1 || undefined}
                onChange={setSlot2}
              />
            </Card>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button disabled={busy || !dirty} onClick={() => void saveSlots()}>
              {busy ? "Saving…" : "Save Pàdéyá Picks"}
            </Button>
            <ConfirmAction
              label="Swap Primary / Secondary"
              title="Swap spotlight order?"
              description="Primary and Secondary listings will trade places on this surface."
              confirmLabel="Swap"
              size="sm"
              variant="secondary"
              busy={busy}
              disabled={!slot1 && !slot2}
              onConfirm={() => onSwap()}
            />
          </div>

          {published.length === 0 ? (
            <Alert tone="warning" title="No published listings">
              Publish a listing before assigning it as a Pàdéyá Pick.
            </Alert>
          ) : null}

          <PlacementPreview
            title={
              context === "homepage"
                ? "Homepage Pàdéyá Picks"
                : "Events page Pàdéyá Picks"
            }
            events={previewEvents}
          />
        </div>
      )}
    </DashboardShell>
  );
}
