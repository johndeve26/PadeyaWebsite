import type { EventAgendaItem } from "@/lib/types/events";

export const AGENDA_ITEM_TYPES = [
  { value: "doors_open", label: "Doors open" },
  { value: "performance", label: "Performance" },
  { value: "speaker", label: "Speaker" },
  { value: "break", label: "Break" },
  { value: "networking", label: "Networking" },
  { value: "after_party", label: "After party" },
  { value: "other", label: "Other" },
] as const;

export type AgendaItemType = (typeof AGENDA_ITEM_TYPES)[number]["value"];

const AGENDA_TYPE_VALUES = new Set<string>(
  AGENDA_ITEM_TYPES.map((t) => t.value),
);

const AGENDA_TYPE_ALIASES: Record<string, AgendaItemType> = {
  doors: "doors_open",
  doorsopen: "doors_open",
  "doors open": "doors_open",
  afterparty: "after_party",
  "after party": "after_party",
  "after-party": "after_party",
  set: "performance",
  setlist: "performance",
  music: "performance",
  talk: "speaker",
  panel: "speaker",
  intermission: "break",
  mix: "networking",
  mingle: "networking",
};

/** Coerce free-text / legacy labels into a valid agenda type. */
export function normalizeAgendaType(value: unknown): AgendaItemType {
  if (typeof value !== "string" || !value.trim()) return "other";
  const raw = value.trim();
  if (AGENDA_TYPE_VALUES.has(raw)) return raw as AgendaItemType;
  const key = raw.toLowerCase().replace(/[_-]+/g, " ").replace(/\s+/g, " ");
  const underscored = key.replace(/\s+/g, "_");
  if (AGENDA_TYPE_VALUES.has(underscored)) {
    return underscored as AgendaItemType;
  }
  return AGENDA_TYPE_ALIASES[key] ?? AGENDA_TYPE_ALIASES[underscored] ?? "other";
}

export type StudioAgendaItem = EventAgendaItem & {
  localId: string;
};

export function toLocalInput(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    // Already a datetime-local string
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) {
      return value.slice(0, 16);
    }
    return "";
  }
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function newAgendaItem(
  partial?: Partial<StudioAgendaItem>,
): StudioAgendaItem {
  const { type: partialType, ...rest } = partial ?? {};
  return {
    localId: `agenda-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    title: "",
    description: "",
    start_time: "",
    end_time: "",
    sort_order: 0,
    ...rest,
    type: normalizeAgendaType(partialType ?? "other"),
  };
}

export function toStudioAgendaItems(
  items: EventAgendaItem[],
): StudioAgendaItem[] {
  return items.map((item, index) => ({
    localId: item.id || `agenda-existing-${index}`,
    id: item.id,
    title: item.title ?? "",
    description: item.description ?? "",
    start_time: toLocalInput(item.start_time),
    end_time: toLocalInput(item.end_time),
    type: normalizeAgendaType(item.type),
    sort_order: item.sort_order ?? index,
  }));
}

export function agendaEndAfterStartError(
  start: string | null | undefined,
  end: string | null | undefined,
): string | null {
  if (!start?.trim() || !end?.trim()) return null;
  const startMs = new Date(start).getTime();
  const endMs = new Date(end).getTime();
  if (Number.isNaN(startMs) || Number.isNaN(endMs)) return null;
  if (endMs <= startMs) return "End time must be after start time.";
  return null;
}
