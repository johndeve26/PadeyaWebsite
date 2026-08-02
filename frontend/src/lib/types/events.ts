export type EventStatus =
  | "draft"
  | "published"
  | "paused"
  | "completed"
  | "cancelled"
  | "rejected"
  | "archived";

export type TicketKind =
  | "free"
  | "free_rsvp"
  | "regular"
  | "early_bird"
  | "vip"
  | "vvip"
  | "table"
  | "group"
  | "invite_only"
  | "hidden"
  | "donation"
  | (string & {});

export type EventType =
  | "public"
  | "private"
  | "invite_only"
  | "secret_location"
  | "online"
  | "hybrid";

export type EventVisibility =
  | "listed"
  | "unlisted"
  | "password_protected"
  | "approval_required";

export type LocationVisibility =
  | "full_public"
  | "area_only"
  | "hidden_until_payment"
  | "hidden_until_24h_before"
  | "hidden_until_manual_approval"
  | "online_only";

export type EventCategory = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
};

export type EventVenue = {
  id?: string;
  name: string;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  notes?: string | null;
};

export type TicketType = {
  id: string;
  event_id: string;
  name: string;
  type: TicketKind | string;
  description: string | null;
  price: string | number;
  quantity: number;
  seats_per_unit?: number;
  min_per_order: number;
  max_per_order: number;
  sale_start: string | null;
  sale_end: string | null;
  visibility: string;
  benefits: string | null;
  transfer_allowed?: boolean;
  refund_allowed?: boolean;
  access_code?: string | null;
  waitlist_enabled?: boolean;
  table_perks?: string | null;
  reservation_hold_minutes?: number | null;
  quantity_sold?: number;
  quantity_reserved?: number;
  status: string;
};

export type EventMedia = {
  id: string;
  url: string;
  media_type: string;
  alt_text: string | null;
  sort_order: number;
};

export type EventAgendaItem = {
  id?: string;
  title: string;
  description?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  type: string;
  sort_order?: number;
};

export type EventPerson = {
  id?: string;
  name: string;
  role?: string | null;
  bio?: string | null;
  image_url?: string | null;
  social_url?: string | null;
  performance_time?: string | null;
  sort_order?: number;
};

export type EventCheckoutQuestion = {
  id?: string;
  label: string;
  type: string;
  required?: boolean;
  options?: string[] | null;
  help_text?: string | null;
  sort_order?: number;
  status?: "active" | "archived" | string;
  archived_at?: string | null;
};

export type EventPublishChecklist = {
  basics_complete: boolean;
  category_complete: boolean;
  venue_privacy_complete: boolean;
  date_complete: boolean;
  has_ticket_type: boolean;
  banner_ready: boolean;
  refund_policy_selected: boolean;
  check_in_settings_complete: boolean;
  seo_complete: boolean;
  preview_checked: boolean;
  ready_to_submit: boolean;
};

export type EventItem = {
  id: string;
  title: string;
  slug: string;
  description: string;
  short_tagline?: string | null;
  vibe?: string | null;
  event_type?: EventType | string;
  visibility?: EventVisibility | string;
  category_id: string | null;
  primary_category_id?: string | null;
  host_id: string;
  start_datetime: string;
  end_datetime: string;
  doors_open_datetime?: string | null;
  timezone?: string;
  venue_name: string | null;
  venue_type?: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  country?: string | null;
  area?: string | null;
  postcode?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  google_place_id?: string | null;
  formatted_address?: string | null;
  google_maps_share_url?: string | null;
  google_maps_place_url?: string | null;
  location_id?: string | null;
  location?: {
    slug: string;
    name: string;
    kind: string;
    ancestors?: { slug: string; name: string; kind: string }[];
  } | null;
  public_location_label?: string | null;
  approximate_latitude?: string | null;
  approximate_longitude?: string | null;
  approximate_map_label?: string | null;
  location_visibility?: LocationVisibility | string;
  reveal_timing?: string;
  reveal_note?: string | null;
  online_event_url?: string | null;
  online_url_reveal_rule?: string;
  location_address_revealed?: boolean;
  location_privacy_message?: string | null;
  location_map_mode?: "exact" | "approximate" | "none" | string;
  map_latitude?: string | null;
  map_longitude?: string | null;
  map_label?: string | null;
  map_open_url?: string | null;
  distance_km?: number | null;
  distance_label?: string | null;
  distance_is_approximate?: boolean;
  has_valid_coordinates?: boolean | null;
  banner_url: string | null;
  mobile_banner_url?: string | null;
  teaser_video_url?: string | null;
  social_share_image_url?: string | null;
  brand_accent_override?: string | null;
  sponsor_logo_urls?: string[] | null;
  capacity: number | null;
  refund_policy: string | null;
  refund_policy_type?: string | null;
  refund_policy_text?: string | null;
  cancellation_policy?: string | null;
  age_restriction: string | null;
  id_required?: boolean;
  safety_notice?: string | null;
  terms_acknowledgement?: string | null;
  door_sales_allowed?: boolean;
  allow_merch_only_checkout?: boolean;
  open_ambassadors_enabled?: boolean;
  open_ambassador_commission_percent?: string | number;
  re_entry_allowed?: boolean;
  check_in_start_time?: string | null;
  check_in_end_time?: string | null;
  dress_code?: string | null;
  accessibility_notes?: string | null;
  parking_info?: string | null;
  what_to_expect?: string | null;
  what_to_bring?: string | null;
  prohibited_items?: string | null;
  entry_requirements?: string | null;
  status: EventStatus;
  featured: boolean;
  seo_title: string | null;
  seo_description: string | null;
  social_share_title?: string | null;
  social_share_description?: string | null;
  hashtags?: string[] | null;
  discoverable_keywords?: string[] | null;
  rejection_reason: string | null;
  admin_flagged?: boolean;
  admin_flagged_at?: string | null;
  admin_flag_reason?: string | null;
  published_at: string | null;
  created_at: string;
  category?: EventCategory | null;
  venue?: EventVenue | null;
  media?: EventMedia[];
  ticket_types?: TicketType[];
  agenda_items?: EventAgendaItem[];
  people?: EventPerson[];
  checkout_questions?: EventCheckoutQuestion[];
  host_display_name?: string | null;
  host_slug?: string | null;
  publish_checklist?: EventPublishChecklist | null;
};

export type HostProfile = {
  bio: string | null;
  website: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  avatar_url: string | null;
  cover_url: string | null;
  social_links: Record<string, string> | null;
};

export type HostTaxonomy = {
  host_type_slugs: string[];
  category_slugs: string[];
  audience_slugs: string[];
  primary_city_slug: string | null;
  service_area_slugs: string[];
  niche_positioning: string | null;
};

export type Host = {
  id: string;
  display_name: string;
  slug: string;
  status: string;
  created_at: string;
  profile: HostProfile | null;
  taxonomy?: HostTaxonomy | null;
  gender?: string | null;
  gender_short?: string | null;
  gender_label?: string | null;
  gender_visible?: boolean;
  shows_personal_gender?: boolean;
};
