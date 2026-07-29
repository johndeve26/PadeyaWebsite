export type FanConnectRequestPolicy =
  | "same_event"
  | "same_host"
  | "public_passports"
  | "nobody";

export type FanConnectSettings = {
  fan_connect_enabled: boolean;
  discoverable_for_same_events: boolean;
  discoverable_for_similar_interests: boolean;
  allow_connection_requests: boolean;
  show_shared_hosts: boolean;
  show_shared_categories: boolean;
  show_shared_public_events: boolean;
  show_public_city: boolean;
  hide_private_events_always: boolean;
  /** Most permissive selected policy (legacy / analytics). */
  request_policy: FanConnectRequestPolicy | string;
  /** Multi-select who-can-request options (OR). `nobody` is exclusive. */
  request_policies?: FanConnectRequestPolicy[] | string[];
};

export type SharedEventChip = {
  event_id: string;
  title: string;
  slug: string;
  path: string;
  city?: string | null;
};

export type SharedHostChip = {
  host_id: string;
  display_name: string;
  username?: string | null;
};

export type SharedContext = {
  events: SharedEventChip[];
  hosts: SharedHostChip[];
  categories: string[];
};

export type CanConnect = {
  allowed: boolean;
  reasons: string[];
  denials: string[];
  /** Present when denials include "self". */
  message?: string | null;
  shared_context: SharedContext;
  connection_status: string | null;
  connection_id: string | null;
  thread_id: string | null;
  relationship_status?: string | null;
  can_send_connect_request?: boolean | null;
  cannot_connect_reason?: string | null;
  cooldown_until?: string | null;
  viewer_declined_target?: boolean | null;
  target_declined_viewer?: boolean | null;
  has_incoming_request?: boolean | null;
  has_outgoing_request?: boolean | null;
};

export type FanConnectCounterpart = {
  user_id?: string | null;
  display_name: string;
  username?: string | null;
  avatar_url?: string | null;
  tagline?: string | null;
  gender?: string | null;
  gender_short?: string | null;
  gender_label?: string | null;
  gender_visible?: boolean;
};

export type FanConnection = {
  id: string;
  status: string;
  direction: string;
  counterpart: FanConnectCounterpart;
  message?: string | null;
  score?: number;
  reasons?: { code: string; label: string }[];
  shared_context?: SharedContext | null;
  thread_id?: string | null;
  created_at: string;
  requested_at?: string | null;
  accepted_at?: string | null;
  responded_at?: string | null;
};

export type FanConnectSuggestionReason = {
  code: string;
  label: string;
};

export type FanConnectSuggestionBadge = {
  slug: string;
  name: string;
};

export type FanConnectSuggestionMode =
  | "mixed"
  | "near_me"
  | "same_event"
  | "connections_of_connections"
  | "same_interests"
  | "new_people";

export type FanConnectSuggestion = {
  user_id?: string | null;
  display_name: string;
  username: string;
  avatar_url?: string | null;
  tagline?: string | null;
  public_city?: string | null;
  badges?: FanConnectSuggestionBadge[];
  match_label?: string | null;
  recommendation_label?: string | null;
  score?: number;
  score_band?: string;
  reasons?: FanConnectSuggestionReason[];
  distance_label?: string | null;
  mutual_connection_count?: number | null;
  connection_status?: string | null;
  cta_state?: string;
  cooldown_until?: string | null;
  viewer_declined_target?: boolean | null;
  can_send_connect_request?: boolean | null;
  shared_context: SharedContext;
};

export type FanConnectSuggestionsPage = {
  items: FanConnectSuggestion[];
  page: number;
  limit: number;
  total: number;
  next_cursor?: string | null;
  mode?: FanConnectSuggestionMode | string;
  empty_title?: string | null;
  empty_description?: string | null;
};

export type FanConnectLocationPreference = {
  city?: string | null;
  area?: string | null;
  country?: string | null;
  precision: "city" | "area" | "approximate" | string;
  latitude_approx?: string | null;
  longitude_approx?: string | null;
  consented_at?: string | null;
  updated_at?: string | null;
};

export type ConnectEvent = {
  event_id: string;
  title: string;
  slug: string;
  path: string;
  city?: string | null;
  start_datetime?: string | null;
  suggestion_count: number;
};

export type FanConnectAdminOverview = {
  connect_enabled_users: number;
  pending_requests: number;
  accepted_connections: number;
  blocked_connections: number;
  fan_fan_threads: number;
  fan_fan_reports: number;
  message_blocks: number;
  open_reports?: number;
};

export type FanConnectAdminBlock = {
  id: string;
  blocker_user_id?: string | null;
  blocked_user_id?: string | null;
  blocker_display_name: string;
  blocker_username?: string | null;
  blocked_display_name: string;
  blocked_username?: string | null;
  reason?: string | null;
  created_at: string;
};

export type FanConnectAdminConnectContext = {
  connection_status?: string | null;
  reason_labels?: string[];
  pair_blocked?: boolean;
};

export type FanConnectAdminReport = {
  id: string;
  thread_id: string | null;
  thread_type?: string | null;
  message_report_id?: string | null;
  reason: string;
  details?: string | null;
  status: string;
  reporter_user_id: string;
  reported_user_id: string;
  reporter_display_name: string;
  reported_display_name: string;
  reporter_username?: string | null;
  reported_username?: string | null;
  reported_connect_enabled?: boolean;
  connection_context?: FanConnectAdminConnectContext | null;
  created_at: string;
  admin_notes?: string | null;
  message_preview?: string | null;
};

export type FanConnectAdminUserHistory = {
  user_id: string;
  display_name: string;
  username?: string | null;
  fan_connect_enabled: boolean;
  reports_about: FanConnectAdminReport[];
  reports_filed: FanConnectAdminReport[];
  blocks_as_blocker: FanConnectAdminBlock[];
  blocks_as_blocked: FanConnectAdminBlock[];
};
