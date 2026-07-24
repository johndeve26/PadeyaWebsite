import type { EventPublishChecklist } from "@/lib/types/events";

import type { EventStudioValues } from "./types";

export const PUBLISH_CHECKLIST_ITEMS: {
  key: keyof EventPublishChecklist;
  label: string;
}[] = [
  { key: "basics_complete", label: "Basics complete" },
  { key: "category_complete", label: "Category selected" },
  { key: "venue_privacy_complete", label: "Location/privacy configured" },
  { key: "date_complete", label: "Date/time complete" },
  { key: "has_ticket_type", label: "At least one ticket type" },
  { key: "banner_ready", label: "Banner or placeholder ready" },
  { key: "refund_policy_selected", label: "Refund policy selected" },
  { key: "check_in_settings_complete", label: "Check-in settings configured" },
  { key: "seo_complete", label: "SEO ready" },
  { key: "preview_checked", label: "Preview checked" },
];

export function buildLocalPublishChecklist(
  values: EventStudioValues,
  saved?: EventPublishChecklist | null,
): EventPublishChecklist {
  const basics_complete =
    Boolean(values.title.trim() && values.description.trim().length >= 10) ||
    Boolean(saved?.basics_complete);
  const category_complete =
    Boolean(values.category_id) || Boolean(saved?.category_complete);
  const venue_privacy_complete =
    Boolean(
      values.location_visibility === "online_only" ||
        values.venue_name.trim() ||
        values.public_location_label.trim() ||
        values.location_id,
    ) || Boolean(saved?.venue_privacy_complete);
  const date_complete =
    Boolean(values.start_datetime && values.end_datetime) ||
    Boolean(saved?.date_complete);
  const has_ticket_type =
    values.ticket_drafts.some((t) => t.name.trim()) ||
    Boolean(saved?.has_ticket_type);
  // Studio always has listing placeholders when no custom banner is set.
  const banner_ready = true;
  const refund_policy_selected = Boolean(values.refund_policy_type);
  const check_in_settings_complete = Boolean(
    values.check_in_start_time ||
      values.doors_open_datetime ||
      values.start_datetime,
  );
  const seo_complete = Boolean(
    values.seo_title.trim() ||
      values.title.trim() ||
      saved?.seo_complete,
  );
  const preview_checked = Boolean(values.preview_checked);
  const ready_to_submit = [
    basics_complete,
    category_complete,
    venue_privacy_complete,
    date_complete,
    has_ticket_type,
    banner_ready,
    refund_policy_selected,
    check_in_settings_complete,
    seo_complete,
    preview_checked,
  ].every(Boolean);

  return {
    basics_complete,
    category_complete,
    venue_privacy_complete,
    date_complete,
    has_ticket_type,
    banner_ready,
    refund_policy_selected,
    check_in_settings_complete,
    seo_complete,
    preview_checked,
    ready_to_submit,
  };
}

export function missingChecklistLabels(
  checklist: EventPublishChecklist,
): string[] {
  return PUBLISH_CHECKLIST_ITEMS.filter((item) => {
    if (item.key === "ready_to_submit") return false;
    return !checklist[item.key];
  }).map((item) => item.label);
}

export function previewCheckedStorageKey(eventId: string | undefined) {
  return eventId ? `padeya:studio:preview_checked:${eventId}` : null;
}
