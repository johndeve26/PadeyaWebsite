import type { EventItem, EventMedia, TicketType } from "@/lib/types/events";
import { normalizeCssColor } from "@/lib/css-color";

import {
  agendaEndAfterStartError,
  normalizeAgendaType,
  toLocalInput,
  toStudioAgendaItems,
  type StudioAgendaItem,
} from "./agenda-utils";
import { toStudioPeople, type StudioPerson } from "./people-utils";
import {
  toStudioQuestions,
  type StudioQuestion,
} from "./question-utils";
import { scrubPrivateAddress, suggestSeoCopy } from "./seo-utils";

export { agendaEndAfterStartError, toLocalInput } from "./agenda-utils";
export type { StudioAgendaItem } from "./agenda-utils";
export type { StudioPerson } from "./people-utils";
export type { StudioQuestion } from "./question-utils";
export {
  REFUND_POLICY_TYPES,
  policyFieldsError,
  refundPolicyLabel,
  refundPolicyNeedsText,
} from "./policy-utils";
export {
  publicSeoPlaceLabel,
  resolvedSeoFields,
  scrubPrivateAddress,
  suggestSeoCopy,
} from "./seo-utils";

export const STUDIO_STEPS = [
  { id: "basics", label: "Basics", description: "Title, category, identity" },
  {
    id: "location",
    label: "Location & Privacy",
    description: "Place and reveal rules",
  },
  {
    id: "schedule",
    label: "Schedule & Agenda",
    description: "Dates and run-of-show",
  },
  {
    id: "tickets",
    label: "Tickets & Access",
    description: "Tiers and who can find it",
  },
  {
    id: "media",
    label: "Media & Branding",
    description: "Banner and visuals",
  },
  {
    id: "lineup",
    label: "Guests / Performers / Speakers",
    description: "Who is on the bill",
  },
  {
    id: "questions",
    label: "Attendee Questions",
    description: "Checkout questions",
  },
  {
    id: "policies",
    label: "Policies & Safety",
    description: "Refunds, door, logistics",
  },
  {
    id: "seo",
    label: "SEO & Discovery",
    description: "Search and share copy",
  },
  {
    id: "merchandise",
    label: "Merchandise",
    description: "Optional pickup merch",
  },
  {
    id: "publish",
    label: "Preview & Publish",
    description: "Checklist and submit",
  },
] as const;

export type StudioStepId = (typeof STUDIO_STEPS)[number]["id"];

const LEGACY_STEP_MAP: Record<string, StudioStepId> = {
  venue: "location",
  guest: "lineup",
};

/** Resolve ?step= query to a canonical StudioStepId. */
export function parseStudioStep(raw: string | null | undefined): StudioStepId {
  if (!raw) return "basics";
  const key = raw.trim().toLowerCase();
  if (LEGACY_STEP_MAP[key]) return LEGACY_STEP_MAP[key];
  if (STUDIO_STEPS.some((s) => s.id === key)) return key as StudioStepId;
  return "basics";
}

export type StudioTicketDraft = {
  localId: string;
  id?: string;
  name: string;
  type: string;
  description: string;
  price: string;
  quantity: string;
  seats_per_unit: string;
  min_per_order: string;
  max_per_order: string;
  sale_start: string;
  sale_end: string;
  visibility: string;
  benefits: string;
  transfer_allowed: boolean;
  refund_allowed: boolean;
  access_code: string;
  waitlist_enabled: boolean;
  table_perks: string;
  reservation_hold_minutes: string;
  quantity_sold?: number;
  quantity_reserved?: number;
  status?: string;
};

export function ticketHasSales(draft: StudioTicketDraft): boolean {
  return (draft.quantity_sold ?? 0) > 0 || (draft.quantity_reserved ?? 0) > 0;
}

export function ticketSaleWindowError(
  saleStart: string,
  saleEnd: string,
): string | null {
  if (!saleStart.trim() || !saleEnd.trim()) return null;
  const start = new Date(saleStart).getTime();
  const end = new Date(saleEnd).getTime();
  if (Number.isNaN(start) || Number.isNaN(end)) return null;
  if (end <= start) return "Sale end must be after sale start.";
  return null;
}

export type EventStudioValues = {
  title: string;
  slug: string;
  short_tagline: string;
  description: string;
  category_id: string;
  vibe: string;
  event_type: string;
  visibility: string;
  venue_name: string;
  venue_type: string;
  address: string;
  country: string;
  state: string;
  city: string;
  area: string;
  postcode: string;
  latitude: string;
  longitude: string;
  google_place_id: string;
  formatted_address: string;
  google_maps_share_url: string;
  google_maps_place_url: string;
  location_id: string;
  public_location_label: string;
  approximate_latitude: string;
  approximate_longitude: string;
  approximate_map_label: string;
  location_visibility: string;
  reveal_timing: string;
  reveal_note: string;
  /** Host-only arrival note; stored on nested venue.notes for ticket holders. */
  directions_note: string;
  online_event_url: string;
  online_url_reveal_rule: string;
  start_datetime: string;
  end_datetime: string;
  doors_open_datetime: string;
  timezone: string;
  agenda_items: StudioAgendaItem[];
  ticket_drafts: StudioTicketDraft[];
  banner_url: string;
  mobile_banner_url: string;
  gallery_urls: string;
  /** Server media rows (for targeted gallery delete). Not sent in event PATCH. */
  media_items: EventMedia[];
  teaser_video_url: string;
  sponsor_logo_urls: string;
  social_share_image_url: string;
  brand_accent_override: string;
  people: StudioPerson[];
  checkout_questions: StudioQuestion[];
  entry_requirements: string;
  dress_code: string;
  accessibility_notes: string;
  parking_info: string;
  what_to_expect: string;
  what_to_bring: string;
  prohibited_items: string;
  refund_policy_type: string;
  refund_policy_text: string;
  cancellation_policy: string;
  age_restriction: string;
  id_required: boolean;
  safety_notice: string;
  terms_acknowledgement: string;
  door_sales_allowed: boolean;
  open_ambassadors_enabled: boolean;
  open_ambassador_commission_percent: string;
  re_entry_allowed: boolean;
  check_in_start_time: string;
  check_in_end_time: string;
  capacity: string;
  seo_title: string;
  seo_description: string;
  social_share_title: string;
  social_share_description: string;
  hashtags: string;
  discoverable_keywords: string;
  preview_checked: boolean;
};

export function studioStepCompletion(
  values: EventStudioValues,
): Partial<Record<StudioStepId, boolean>> {
  return {
    basics: Boolean(values.title && values.description.length >= 10),
    location: Boolean(
      values.location_visibility === "online_only" ||
        values.venue_name ||
        values.public_location_label ||
        values.location_id ||
        values.city ||
        values.area,
    ),
    schedule: Boolean(
      values.start_datetime &&
        values.end_datetime &&
        !agendaEndAfterStartError(values.start_datetime, values.end_datetime),
    ),
    tickets: values.ticket_drafts.length > 0,
    media: Boolean(values.banner_url),
    lineup: values.people.length > 0,
    questions: values.checkout_questions.length > 0,
    policies: Boolean(values.refund_policy_type),
    seo: Boolean(values.seo_title || values.title),
    // Optional — never blocks publish; always marked ready so Continue is soft.
    merchandise: true,
    publish: values.preview_checked,
  };
}

export function emptyStudioValues(): EventStudioValues {
  return {
    title: "",
    slug: "",
    short_tagline: "",
    description: "",
    category_id: "",
    vibe: "",
    event_type: "public",
    visibility: "listed",
    venue_name: "",
    venue_type: "",
    address: "",
    country: "",
    state: "",
    city: "",
    area: "",
    postcode: "",
    latitude: "",
    longitude: "",
    google_place_id: "",
    formatted_address: "",
    google_maps_share_url: "",
    google_maps_place_url: "",
    location_id: "",
    public_location_label: "",
    approximate_latitude: "",
    approximate_longitude: "",
    approximate_map_label: "",
    location_visibility: "full_public",
    reveal_timing: "immediately",
    reveal_note: "",
    directions_note: "",
    online_event_url: "",
    online_url_reveal_rule: "after_payment",
    start_datetime: "",
    end_datetime: "",
    doors_open_datetime: "",
    timezone: "Africa/Lagos",
    agenda_items: [],
    ticket_drafts: [],
    banner_url: "",
    mobile_banner_url: "",
    gallery_urls: "",
    media_items: [],
    teaser_video_url: "",
    sponsor_logo_urls: "",
    social_share_image_url: "",
    brand_accent_override: "",
    people: [],
    checkout_questions: [],
    entry_requirements: "",
    dress_code: "",
    accessibility_notes: "",
    parking_info: "",
    what_to_expect: "",
    what_to_bring: "",
    prohibited_items: "",
    refund_policy_type: "admin_controlled",
    refund_policy_text: "",
    cancellation_policy: "",
    age_restriction: "",
    id_required: false,
    safety_notice: "",
    terms_acknowledgement: "",
    door_sales_allowed: true,
    open_ambassadors_enabled: false,
    open_ambassador_commission_percent: "5",
    re_entry_allowed: false,
    check_in_start_time: "",
    check_in_end_time: "",
    capacity: "",
    seo_title: "",
    seo_description: "",
    social_share_title: "",
    social_share_description: "",
    hashtags: "",
    discoverable_keywords: "",
    preview_checked: false,
  };
}

function splitLines(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export function ticketsToStudioDrafts(
  tickets: TicketType[],
): StudioTicketDraft[] {
  return tickets.map((t, i) => ({
    localId: t.id || `existing-${i}`,
    id: t.id,
    name: t.name,
    type: t.type === "free" ? "free_rsvp" : String(t.type),
    description: t.description ?? "",
    price: String(t.price ?? "0"),
    quantity: String(t.quantity ?? 0),
    seats_per_unit: String(t.seats_per_unit ?? 1),
    min_per_order: String(t.min_per_order ?? 1),
    max_per_order: String(t.max_per_order ?? 10),
    sale_start: toLocalInput(t.sale_start),
    sale_end: toLocalInput(t.sale_end),
    visibility: t.visibility ?? "public",
    benefits: t.benefits ?? "",
    transfer_allowed: t.transfer_allowed ?? true,
    refund_allowed: t.refund_allowed ?? false,
    access_code: t.access_code ?? "",
    waitlist_enabled: t.waitlist_enabled ?? false,
    table_perks: t.table_perks ?? "",
    reservation_hold_minutes: t.reservation_hold_minutes?.toString() ?? "",
    quantity_sold: t.quantity_sold ?? 0,
    quantity_reserved: t.quantity_reserved ?? 0,
    status: t.status ?? "active",
  }));
}

export function eventToStudioValues(
  event: EventItem,
  tickets?: TicketType[],
): EventStudioValues {
  const gallery = (event.media ?? [])
    .filter((m) => m.media_type === "gallery")
    .map((m) => m.url)
    .join("\n");
  const ticketSource = tickets ?? event.ticket_types ?? [];
  return {
    ...emptyStudioValues(),
    title: event.title,
    slug: event.slug,
    short_tagline: event.short_tagline ?? "",
    description: event.description,
    category_id: event.category_id ?? "",
    vibe: event.vibe ?? "",
    event_type: event.event_type ?? "public",
    visibility: event.visibility ?? "listed",
    venue_name: event.venue_name ?? "",
    venue_type: event.venue_type ?? "",
    address: event.address ?? "",
    country: event.country ?? event.venue?.country ?? "",
    city: event.city ?? "",
    state: event.state ?? "",
    area:
      event.area ||
      (event.location?.kind === "area" ? event.location.name : "") ||
      "",
    postcode: event.postcode ?? "",
    latitude: event.latitude ?? event.venue?.latitude ?? "",
    longitude: event.longitude ?? event.venue?.longitude ?? "",
    google_place_id: event.google_place_id ?? "",
    formatted_address: event.formatted_address ?? "",
    google_maps_share_url: event.google_maps_share_url ?? "",
    google_maps_place_url: event.google_maps_place_url ?? "",
    location_id: event.location_id ?? "",
    public_location_label: event.public_location_label ?? "",
    approximate_latitude: event.approximate_latitude ?? "",
    approximate_longitude: event.approximate_longitude ?? "",
    approximate_map_label: event.approximate_map_label ?? "",
    location_visibility: event.location_visibility ?? "full_public",
    reveal_timing: event.reveal_timing ?? "immediately",
    reveal_note: event.reveal_note ?? "",
    directions_note: event.venue?.notes ?? "",
    online_event_url: event.online_event_url ?? "",
    online_url_reveal_rule: event.online_url_reveal_rule ?? "after_payment",
    start_datetime: toLocalInput(event.start_datetime),
    end_datetime: toLocalInput(event.end_datetime),
    doors_open_datetime: toLocalInput(event.doors_open_datetime),
    timezone: event.timezone ?? "Africa/Lagos",
    agenda_items: toStudioAgendaItems(event.agenda_items ?? []),
    ticket_drafts: ticketsToStudioDrafts(ticketSource),
    banner_url: event.banner_url ?? "",
    mobile_banner_url: event.mobile_banner_url ?? "",
    gallery_urls: gallery,
    media_items: event.media ?? [],
    teaser_video_url: event.teaser_video_url ?? "",
    sponsor_logo_urls: (event.sponsor_logo_urls ?? []).join("\n"),
    social_share_image_url: event.social_share_image_url ?? "",
    brand_accent_override: event.brand_accent_override ?? "",
    people: toStudioPeople(event.people ?? []),
    checkout_questions: toStudioQuestions(event.checkout_questions ?? []),
    entry_requirements: event.entry_requirements ?? "",
    dress_code: event.dress_code ?? "",
    accessibility_notes: event.accessibility_notes ?? "",
    parking_info: event.parking_info ?? "",
    what_to_expect: event.what_to_expect ?? "",
    what_to_bring: event.what_to_bring ?? "",
    prohibited_items: event.prohibited_items ?? "",
    refund_policy_type: event.refund_policy_type ?? event.refund_policy ?? "admin_controlled",
    refund_policy_text: event.refund_policy_text ?? "",
    cancellation_policy: event.cancellation_policy ?? "",
    age_restriction: event.age_restriction ?? "",
    id_required: event.id_required ?? false,
    safety_notice: event.safety_notice ?? "",
    terms_acknowledgement: event.terms_acknowledgement ?? "",
    door_sales_allowed: event.door_sales_allowed ?? true,
    open_ambassadors_enabled: event.open_ambassadors_enabled ?? false,
    open_ambassador_commission_percent: String(
      event.open_ambassador_commission_percent ?? "5",
    ),
    re_entry_allowed: event.re_entry_allowed ?? false,
    check_in_start_time: toLocalInput(event.check_in_start_time),
    check_in_end_time: toLocalInput(event.check_in_end_time),
    capacity: event.capacity?.toString() ?? "",
    seo_title: event.seo_title ?? "",
    seo_description: event.seo_description ?? "",
    social_share_title: event.social_share_title ?? "",
    social_share_description: event.social_share_description ?? "",
    hashtags: (event.hashtags ?? []).join(", "),
    discoverable_keywords: (event.discoverable_keywords ?? []).join(", "),
    preview_checked: event.publish_checklist?.preview_checked ?? false,
  };
}

export function studioValuesToPayload(
  values: EventStudioValues,
  opts?: { includeSlug?: boolean; categoryName?: string | null },
): Record<string, unknown> {
  const iso = (v: string) => (v ? new Date(v).toISOString() : null);
  const suggested = suggestSeoCopy(values, opts?.categoryName);
  const scrub = (text: string) =>
    scrubPrivateAddress(text, values.address).trim();
  const seoTitle = scrub(values.seo_title || suggested.seo_title);
  const seoDescription = scrub(
    values.seo_description || suggested.seo_description,
  );
  const socialTitle = scrub(
    values.social_share_title || suggested.social_share_title,
  );
  const socialDescription = scrub(
    values.social_share_description || suggested.social_share_description,
  );
  const hashtags = scrub(values.hashtags || suggested.hashtags);
  const keywords = scrub(
    values.discoverable_keywords || suggested.discoverable_keywords,
  );
  const payload: Record<string, unknown> = {
    title: values.title,
    description: values.description,
    short_tagline: values.short_tagline || null,
    vibe: values.vibe || null,
    event_type: values.event_type,
    visibility: values.visibility,
    category_id: values.category_id || null,
    start_datetime: new Date(values.start_datetime).toISOString(),
    end_datetime: new Date(values.end_datetime).toISOString(),
    doors_open_datetime: iso(values.doors_open_datetime),
    timezone: values.timezone || "Africa/Lagos",
    venue_name: values.venue_name || null,
    venue_type: values.venue_type || null,
    address: values.address || null,
    city: values.city || null,
    state: values.state || null,
    country: values.country || null,
    area: values.area || null,
    postcode: values.postcode || null,
    latitude: values.latitude || null,
    longitude: values.longitude || null,
    google_place_id: values.google_place_id || null,
    formatted_address: values.formatted_address || null,
    google_maps_share_url: values.google_maps_share_url || null,
    google_maps_place_url: values.google_maps_place_url || null,
    location_id: values.location_id || null,
    public_location_label: values.public_location_label || null,
    approximate_latitude: values.approximate_latitude || null,
    approximate_longitude: values.approximate_longitude || null,
    approximate_map_label: values.approximate_map_label || null,
    location_visibility: values.location_visibility,
    reveal_timing: values.reveal_timing,
    reveal_note: values.reveal_note || null,
    online_event_url: values.online_event_url || null,
    online_url_reveal_rule: values.online_url_reveal_rule,
    banner_url: values.banner_url || null,
    mobile_banner_url: values.mobile_banner_url || null,
    teaser_video_url: values.teaser_video_url || null,
    social_share_image_url: values.social_share_image_url || null,
    brand_accent_override: normalizeCssColor(values.brand_accent_override),
    sponsor_logo_urls: splitLines(values.sponsor_logo_urls),
    gallery_urls: splitLines(values.gallery_urls),
    capacity: values.capacity ? Number(values.capacity) : null,
    refund_policy: values.refund_policy_type || null,
    refund_policy_type: values.refund_policy_type || null,
    refund_policy_text: values.refund_policy_text || null,
    cancellation_policy: values.cancellation_policy || null,
    age_restriction: values.age_restriction || null,
    id_required: values.id_required,
    safety_notice: values.safety_notice || null,
    terms_acknowledgement: values.terms_acknowledgement || null,
    door_sales_allowed: values.door_sales_allowed,
    open_ambassadors_enabled: values.open_ambassadors_enabled,
    open_ambassador_commission_percent: Number(
      values.open_ambassador_commission_percent || "5",
    ),
    re_entry_allowed: values.re_entry_allowed,
    check_in_start_time: iso(values.check_in_start_time),
    check_in_end_time: iso(values.check_in_end_time),
    dress_code: values.dress_code || null,
    accessibility_notes: values.accessibility_notes || null,
    parking_info: values.parking_info || null,
    what_to_expect: values.what_to_expect || null,
    what_to_bring: values.what_to_bring || null,
    prohibited_items: values.prohibited_items || null,
    entry_requirements: values.entry_requirements || null,
    seo_title: seoTitle || null,
    seo_description: seoDescription || null,
    social_share_title: socialTitle || null,
    social_share_description: socialDescription || null,
    hashtags: splitLines(hashtags),
    discoverable_keywords: splitLines(keywords),
    agenda_items: values.agenda_items
      .filter((item) => item.title.trim())
      .map((item, index) => ({
        ...(item.id ? { id: item.id } : {}),
        title: item.title.trim(),
        description: item.description || null,
        start_time: item.start_time
          ? new Date(item.start_time).toISOString()
          : null,
        end_time: item.end_time ? new Date(item.end_time).toISOString() : null,
        type: normalizeAgendaType(item.type),
        sort_order: index,
      })),
    people: values.people
      .filter((person) => person.name.trim())
      .map((person, index) => ({
        ...(person.id ? { id: person.id } : {}),
        name: person.name.trim(),
        role: person.role || null,
        bio: person.bio || null,
        image_url: person.image_url || null,
        social_url: person.social_url || null,
        performance_time: person.performance_time
          ? new Date(person.performance_time).toISOString()
          : null,
        sort_order: index,
      })),
    checkout_questions: values.checkout_questions
      .filter((q) => q.label.trim() && (q.status ?? "active") !== "archived")
      .map((q, index) => ({
        ...(q.id ? { id: q.id } : {}),
        label: q.label.trim(),
        type: q.type || "short_text",
        required: Boolean(q.required),
        options: q.options?.length ? q.options : null,
        help_text: q.help_text?.trim() || null,
        sort_order: index,
        status: "active",
      })),
    venue: values.venue_name || values.address || values.country
      ? {
          name: values.venue_name || values.public_location_label || "Venue",
          address: values.address || null,
          city: values.city || null,
          state: values.state || null,
          country: values.country || null,
          latitude: values.latitude || null,
          longitude: values.longitude || null,
          notes: values.directions_note || null,
        }
      : null,
  };
  if (opts?.includeSlug && values.slug.trim()) {
    payload.slug = values.slug.trim().toLowerCase();
  }
  return payload;
}

export function ticketDraftToPayload(
  draft: StudioTicketDraft,
  opts?: { forSoldTier?: boolean },
): Record<string, unknown> {
  const type =
    draft.type
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "_")
      .replace(/[^a-z0-9_-]+/g, "_")
      .replace(/_+/g, "_")
      .replace(/^[_-]+|[_-]+$/g, "")
      .slice(0, 32) || "regular";
  const kind = type === "free" ? "free_rsvp" : type;
  const visibility =
    draft.visibility ||
    (kind === "hidden" || kind === "invite_only" ? kind : "public");
  const price = kind === "free_rsvp" ? 0 : Number(draft.price || 0);

  if (opts?.forSoldTier) {
    // After sales: only non-structural fields (orders stay intact).
    return {
      description: draft.description || null,
      sale_start: draft.sale_start
        ? new Date(draft.sale_start).toISOString()
        : null,
      sale_end: draft.sale_end ? new Date(draft.sale_end).toISOString() : null,
      visibility,
      benefits: draft.benefits || null,
      transfer_allowed: draft.transfer_allowed,
      refund_allowed: draft.refund_allowed,
      access_code: draft.access_code || null,
      waitlist_enabled: draft.waitlist_enabled,
      table_perks: kind === "table" ? draft.table_perks || null : null,
      reservation_hold_minutes:
        kind === "table" && draft.reservation_hold_minutes
          ? Number(draft.reservation_hold_minutes)
          : null,
      status: draft.status === "inactive" ? "inactive" : "active",
    };
  }

  return {
    name: draft.name,
    type: kind,
    description: draft.description || null,
    price,
    quantity: Number(draft.quantity || 0),
    seats_per_unit: Number(draft.seats_per_unit || 1),
    min_per_order: Number(draft.min_per_order || 1),
    max_per_order: Number(draft.max_per_order || 10),
    sale_start: draft.sale_start ? new Date(draft.sale_start).toISOString() : null,
    sale_end: draft.sale_end ? new Date(draft.sale_end).toISOString() : null,
    visibility,
    benefits: draft.benefits || null,
    transfer_allowed: draft.transfer_allowed,
    refund_allowed: draft.refund_allowed,
    access_code: draft.access_code || null,
    waitlist_enabled: draft.waitlist_enabled,
    table_perks: kind === "table" ? draft.table_perks || null : null,
    reservation_hold_minutes:
      kind === "table" && draft.reservation_hold_minutes
        ? Number(draft.reservation_hold_minutes)
        : null,
    status: draft.status === "inactive" ? "inactive" : "active",
  };
}
