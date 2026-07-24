"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { PlacementPreview } from "@/components/admin/PlacementPreview";
import { Alert, Button, Card, Input } from "@/components/ui";
import { fetchCategories } from "@/lib/events-api";
import {
  buildPadeyaPicksTitle,
  fromDatetimeLocalValue,
  locationKindForContext,
  needsCategory,
  needsLocation,
  PLACEMENT_CONTEXT_OPTIONS,
  toDatetimeLocalValue,
  type FeaturedPlacementContext,
  type FeaturedPlacementSetUpsert,
  type PlacementContextType,
  type PlacementStatus,
} from "@/lib/placements-api";
import {
  fetchTaxonomyLocations,
  type TaxonomyLocation,
} from "@/lib/taxonomy-api";
import type { EventCategory, EventItem } from "@/lib/types/events";

export type PlacementFormState = {
  context_type: PlacementContextType;
  location_id: string;
  category_id: string;
  slot_1_event_id: string;
  slot_2_event_id: string;
  title_override: string;
  subtitle_override: string;
  badge_text: string;
  starts_at: string;
  ends_at: string;
  status: PlacementStatus;
};

export function emptyPlacementForm(
  defaults?: Partial<PlacementFormState>,
): PlacementFormState {
  return {
    context_type: "events_page",
    location_id: "",
    category_id: "",
    slot_1_event_id: "",
    slot_2_event_id: "",
    title_override: "",
    subtitle_override: "",
    badge_text: "",
    starts_at: "",
    ends_at: "",
    status: "draft",
    ...defaults,
  };
}

export function formFromSet(set: FeaturedPlacementContext): PlacementFormState {
  const slot1 = set.slots.find((s) => s.slot_number === 1 || s.slot_index === 1);
  const slot2 = set.slots.find((s) => s.slot_number === 2 || s.slot_index === 2);
  return emptyPlacementForm({
    context_type: (set.placement_type || set.context_type) as PlacementContextType,
    location_id: set.location_id || "",
    category_id: set.category_id || "",
    slot_1_event_id: slot1?.event_id || "",
    slot_2_event_id: slot2?.event_id || "",
    title_override: set.title_override || "",
    subtitle_override: set.subtitle_override || "",
    badge_text: set.badge_text || "",
    starts_at: toDatetimeLocalValue(set.starts_at),
    ends_at: toDatetimeLocalValue(set.ends_at),
    status: (set.status as PlacementStatus) || "draft",
  });
}

export function formToUpsert(form: PlacementFormState): FeaturedPlacementSetUpsert {
  return {
    context_type: form.context_type,
    location_id: needsLocation(form.context_type) ? form.location_id || null : null,
    category_id: needsCategory(form.context_type) ? form.category_id || null : null,
    slot_1: { event_id: form.slot_1_event_id || null },
    slot_2: { event_id: form.slot_2_event_id || null },
    title_override: form.title_override.trim() || null,
    subtitle_override: form.subtitle_override.trim() || null,
    badge_text: form.badge_text.trim() || null,
    starts_at: fromDatetimeLocalValue(form.starts_at),
    ends_at: fromDatetimeLocalValue(form.ends_at),
    status: form.status,
  };
}

function EventPicker({
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
      .slice(0, 40);
  }, [events, excludeId, q]);

  const selected = events.find((e) => e.id === value);

  return (
    <div className="space-y-2">
      <p className="text-sm font-semibold text-foreground">{label}</p>
      {selected ? (
        <p className="text-sm text-muted-foreground">
          Selected:{" "}
          <span className="font-semibold text-foreground">{selected.title}</span>
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">No event selected</p>
      )}
      <Input
        label="Search events"
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

export function AdminPlacementForm({
  mode,
  initial,
  events,
  busy,
  error,
  lockContext = false,
  onSubmit,
  onCancelHref,
}: {
  mode: "create" | "edit";
  initial: PlacementFormState;
  events: EventItem[];
  busy?: boolean;
  error?: string | null;
  lockContext?: boolean;
  onSubmit: (form: PlacementFormState) => void | Promise<void>;
  onCancelHref: string;
}) {
  const [form, setForm] = useState<PlacementFormState>(initial);
  const [categories, setCategories] = useState<EventCategory[]>([]);
  const [locations, setLocations] = useState<TaxonomyLocation[]>([]);

  const locationKind = locationKindForContext(form.context_type);
  const canSave =
    (!needsLocation(form.context_type) || Boolean(form.location_id)) &&
    (!needsCategory(form.context_type) || Boolean(form.category_id));

  useEffect(() => {
    let alive = true;
    void fetchCategories()
      .then((rows) => {
        if (alive) setCategories(rows.filter((c) => c.is_active !== false));
      })
      .catch(() => {
        if (alive) setCategories([]);
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!locationKind) {
      return;
    }
    let alive = true;
    void fetchTaxonomyLocations({ kind: locationKind })
      .then((rows) => {
        if (!alive) return;
        setLocations(rows);
      })
      .catch(() => {
        if (alive) setLocations([]);
      });
    return () => {
      alive = false;
    };
  }, [locationKind]);

  const selectedLocation = locations.find((l) => l.id === form.location_id);
  const selectedCategory = categories.find((c) => c.id === form.category_id);

  const previewTitle = buildPadeyaPicksTitle({
    context: form.context_type,
    locationName: selectedLocation?.name,
    categoryName: selectedCategory?.name,
    titleOverride: form.title_override,
  });

  const previewEvents = useMemo(() => {
    const out: EventItem[] = [];
    const e1 = events.find((e) => e.id === form.slot_1_event_id);
    const e2 = events.find((e) => e.id === form.slot_2_event_id);
    if (e1) out.push(e1);
    if (e2) out.push(e2);
    return out;
  }, [events, form.slot_1_event_id, form.slot_2_event_id]);

  function patch(partial: Partial<PlacementFormState>) {
    setForm((prev) => ({ ...prev, ...partial }));
  }

  function onContextChange(next: PlacementContextType) {
    patch({
      context_type: next,
      location_id: needsLocation(next) ? form.location_id : "",
      category_id: needsCategory(next) ? form.category_id : "",
    });
  }

  return (
    <form
      className="space-y-5"
      onSubmit={(e) => {
        e.preventDefault();
        if (!canSave || busy) return;
        void onSubmit(form);
      }}
    >
      {error ? <Alert tone="danger" title={error} /> : null}

      <Card className="space-y-4 p-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Placement context
          </p>
          <h2 className="mt-1 text-lg font-extrabold text-foreground">
            {previewTitle}
          </h2>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <label className="block space-y-1.5">
            <span className="text-sm font-semibold">Placement type</span>
            <select
              className="h-11 w-full rounded-[var(--radius-md)] border border-input-border bg-input-background px-3 text-sm text-input-foreground disabled:opacity-60"
              value={form.context_type}
              disabled={lockContext || busy}
              onChange={(e) =>
                onContextChange(e.target.value as PlacementContextType)
              }
            >
              {PLACEMENT_CONTEXT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          {needsLocation(form.context_type) ? (
            <label className="block space-y-1.5">
              <span className="text-sm font-semibold capitalize">
                {locationKind}
              </span>
              <select
                className="h-11 w-full rounded-[var(--radius-md)] border border-input-border bg-input-background px-3 text-sm text-input-foreground"
                value={form.location_id}
                disabled={busy || lockContext}
                onChange={(e) => patch({ location_id: e.target.value })}
              >
                <option value="">Select {locationKind}…</option>
                {(locationKind ? locations : []).map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {needsCategory(form.context_type) ? (
            <label className="block space-y-1.5">
              <span className="text-sm font-semibold">Category</span>
              <select
                className="h-11 w-full rounded-[var(--radius-md)] border border-input-border bg-input-background px-3 text-sm text-input-foreground"
                value={form.category_id}
                disabled={busy || lockContext}
                onChange={(e) => patch({ category_id: e.target.value })}
              >
                <option value="">Select category…</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <label className="block space-y-1.5">
            <span className="text-sm font-semibold">Status</span>
            <select
              className="h-11 w-full rounded-[var(--radius-md)] border border-input-border bg-input-background px-3 text-sm text-input-foreground"
              value={form.status}
              disabled={busy}
              onChange={(e) =>
                patch({ status: e.target.value as PlacementStatus })
              }
            >
              <option value="draft">Draft (inactive)</option>
              <option value="active">Active</option>
              <option value="scheduled">Scheduled</option>
              <option value="archived">Archived</option>
            </select>
          </label>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-4 p-5">
          <EventPicker
            label="Primary Spotlight (slot 1)"
            events={events}
            value={form.slot_1_event_id}
            excludeId={form.slot_2_event_id}
            onChange={(id) => patch({ slot_1_event_id: id })}
          />
        </Card>
        <Card className="space-y-4 p-5">
          <EventPicker
            label="Secondary Spotlight (slot 2)"
            events={events}
            value={form.slot_2_event_id}
            excludeId={form.slot_1_event_id}
            onChange={(id) => patch({ slot_2_event_id: id })}
          />
        </Card>
      </div>

      <Card className="space-y-4 p-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Overrides & schedule
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Optional title/subtitle/badge and start/end window for this placement
            set.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            label="Title override"
            value={form.title_override}
            onChange={(e) => patch({ title_override: e.target.value })}
            placeholder={previewTitle}
          />
          <Input
            label="Badge text"
            value={form.badge_text}
            onChange={(e) => patch({ badge_text: e.target.value })}
            placeholder="Pàdéyá Picks"
          />
          <Input
            label="Subtitle override"
            value={form.subtitle_override}
            onChange={(e) => patch({ subtitle_override: e.target.value })}
            placeholder="Primary and Secondary Spotlight listings…"
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Starts at"
              type="datetime-local"
              value={form.starts_at}
              onChange={(e) => patch({ starts_at: e.target.value })}
            />
            <Input
              label="Ends at"
              type="datetime-local"
              value={form.ends_at}
              onChange={(e) => patch({ ends_at: e.target.value })}
            />
          </div>
        </div>
      </Card>

      <PlacementPreview
        events={previewEvents}
        title={previewTitle}
        description={form.subtitle_override.trim() || undefined}
      />

      {!canSave ? (
        <Alert
          tone="info"
          title="Select the required location and/or category before saving."
        />
      ) : null}

      <div className="flex flex-wrap gap-3">
        <Button type="submit" disabled={!canSave || busy}>
          {busy
            ? "Saving…"
            : mode === "create"
              ? "Create placement"
              : "Save changes"}
        </Button>
        <Link href={onCancelHref}>
          <Button type="button" variant="secondary" disabled={busy}>
            Cancel
          </Button>
        </Link>
      </div>
    </form>
  );
}

/** @deprecated Prefer AdminPlacementForm */
export const FeaturedPlacementForm = AdminPlacementForm;
