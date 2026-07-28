/** Types for newer CRUD/lifecycle resources. */

/** Homepage browse taxonomy rails. */
export type CmsBrowseRail = "interest" | "city" | "price" | "when";

export type CmsBrowseTile = {
  id: string;
  rail: string;
  label: string;
  hint: string | null;
  href: string;
  image_url: string;
  sort_order: number;
  status: string;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CmsBanner = {
  id: string;
  title: string;
  subtitle: string | null;
  image_url: string;
  cta_label: string | null;
  cta_href: string | null;
  sort_order: number;
  status: string;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CmsBlogPost = {
  id: string;
  title: string;
  slug: string;
  excerpt: string | null;
  body: string;
  cover_url: string | null;
  status: string;
  published_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CmsFaq = {
  id: string;
  question: string;
  answer: string;
  category: string;
  sort_order: number;
  status: string;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type VaultSubscription = {
  id: string;
  host_id: string;
  buyer_user_id: string;
  status: string;
  plan_label: string;
  price: string | number;
  currency: string;
  started_at: string | null;
  ends_at: string | null;
  cancelled_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type EventCategory = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
};

export type AuditLog = {
  id: string;
  actor_user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
};

export type UserPublic = {
  id: string;
  /** Email address or Pàdéyá username (with or without @). */
  email: string;
  full_name: string;
  username?: string | null;
  is_active: boolean;
  is_verified: boolean;
  ambassadors_blocked?: boolean;
  roles: string[];
  permissions: string[];
  created_at: string;
  deactivated_at?: string | null;
  security_locked?: boolean;
  security_lock_reason?: string | null;
  under_review?: boolean;
  under_review_reason?: string | null;
  under_review_at?: string | null;
  account_status?: string;
  account_restrictions?: string[];
  restriction_keys?: string[];
  suspension?: {
    id: string;
    status: string;
    reason_category: string;
    reason_category_label: string;
    starts_at: string;
    ends_at: string | null;
    duration_label: string;
  } | null;
};

/** Safe admin directory row — no passwords, tokens, or private payloads. */
export type AdminUserRow = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  ambassadors_blocked: boolean;
  roles: string[];
  created_at: string;
  deactivated_at: string | null;
  security_locked: boolean;
  security_lock_reason: string | null;
  under_review?: boolean;
  account_status?: string;
  /** Active restriction count when list API provides it. */
  restriction_count?: number;
  account_restrictions?: string[];
};

export type AdminUserList = {
  items: AdminUserRow[];
  page: number;
  limit: number;
  total: number;
};

export type AdminUserProfileSection = {
  avatar_url: string | null;
  tagline: string | null;
  bio: string | null;
  passport_visibility: string | null;
  passport_admin_hidden: boolean;
  fan_connect_enabled: boolean;
  fan_connect_status: string;
  ambassador_profile_status: string | null;
  ambassadors_program_blocked: boolean;
  campaigns_joined: number;
};

export type AdminUserAccountSection = {
  email_verified: boolean;
  auth_provider: string;
  roles: string[];
  phone_masked: string | null;
  phone_available: boolean;
  two_factor_status: string;
  active_sessions: number;
  last_active_at: string | null;
};

export type AdminUserActivitySection = {
  tickets_count: number;
  orders_count: number;
  merch_count: number;
  refunds_count: number;
  reviews_count: number;
  host_workspaces_owned: number;
  host_teams_joined: number;
  ambassador_campaigns_joined: number;
};

export type AdminUserActivityKind =
  | "tickets"
  | "orders"
  | "merch"
  | "refunds"
  | "reviews"
  | "hosts"
  | "teams"
  | "ambassadors";

export type AdminUserActivityDetailList = {
  kind: AdminUserActivityKind;
  items: Record<string, unknown>[];
  page: number;
  limit: number;
  total: number;
  finance_fields_included: boolean;
};

export type AdminUserNote = {
  id: string;
  user_id: string;
  note_type: string;
  body: string;
  created_by_admin_id: string;
  created_at: string;
  updated_at: string | null;
};

export type AdminUserFlag = {
  id: string;
  user_id: string;
  flag_type: string;
  severity: string;
  status: string;
  reason: string;
  internal_note: string | null;
  created_by_admin_id: string;
  created_at: string;
  resolved_by_admin_id: string | null;
  resolved_at: string | null;
  resolution_note: string | null;
  updated_at: string;
};

/** Restriction history row from `user_restrictions` (never hard-deleted). */
export type UserRestrictionStatus = "active" | "expired" | "revoked";

export type AdminUserRestriction = {
  id: string;
  user_id: string;
  restriction_key: string;
  status: UserRestrictionStatus;
  reason: string;
  internal_note?: string | null;
  starts_at: string;
  ends_at?: string | null;
  created_by_admin_id: string;
  /** Optional when list/detail expands actor. */
  created_by_email?: string | null;
  created_by_name?: string | null;
  revoked_by_admin_id?: string | null;
  revoked_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminUserModerationSection = {
  flags: string[];
  restrictions: string[];
  suspensions: string[];
  internal_notes: AdminUserNote[];
  admin_flags: AdminUserFlag[];
  /** Restriction history rows when the API returns them. */
  user_restrictions?: AdminUserRestriction[];
  under_review: boolean;
  under_review_reason: string | null;
  under_review_at: string | null;
};

export type AdminUserAuditItem = {
  id: string;
  action: string;
  actor_user_id: string | null;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
};

/** Safe admin user detail — no passwords, tokens, or private payloads. */
export type AdminUserDetail = {
  id: string;
  email: string;
  email_masked: string;
  full_name: string;
  display_name: string;
  username: string | null;
  is_active: boolean;
  is_verified: boolean;
  account_status: string;
  verification_status: string;
  created_at: string;
  deactivated_at: string | null;
  last_active_at: string | null;
  risk_level: string;
  risk_label: string;
  security_locked: boolean;
  security_lock_reason: string | null;
  ambassadors_blocked: boolean;
  under_review: boolean;
  under_review_reason: string | null;
  under_review_at: string | null;
  /** Derived active restriction keys (from history and/or JSON sync). */
  account_restrictions: string[];
  /** Restriction history rows when returned on detail. */
  user_restrictions?: AdminUserRestriction[];
  roles: string[];
  profile: AdminUserProfileSection;
  account: AdminUserAccountSection;
  activity: AdminUserActivitySection;
  moderation: AdminUserModerationSection;
  recent_audit: AdminUserAuditItem[];
};

export type HostTeamPermissionKey =
  | "events.view"
  | "events.create"
  | "events.edit"
  | "events.publish"
  | "events.cancel"
  | "events.archive"
  | "tickets.view"
  | "tickets.scan_qr"
  | "tickets.check_in"
  | "tickets.manage_pricing"
  | "tickets.manage_capacity"
  | "tickets.export_attendees"
  | "tickets.view_refunds"
  | "merch.view"
  | "merch.create"
  | "merch.edit"
  | "merch.manage_inventory"
  | "merch.scan_pickup_qr"
  | "merch.mark_picked_up"
  | "merch.fulfill_orders"
  | "merch.manage_shipping"
  | "merch.manage_discounts"
  | "merch.manage_bundles"
  | "messages.view"
  | "messages.reply"
  | "messages.manage_templates"
  | "messages.report_or_escalate"
  | "sponsors.view"
  | "sponsors.reply"
  | "sponsors.manage_slots"
  | "sponsors.accept_or_reject"
  | "analytics.view_events"
  | "analytics.view_merch"
  | "analytics.view_sponsors"
  | "analytics.export"
  | "team.view"
  | "team.invite"
  | "team.edit_permissions"
  | "team.remove_members"
  | "finance.view_sales_summary"
  | "finance.view_payouts"
  | "finance.manage_payouts"
  | "finance.manage_payout_settings"
  | "ambassadors.view"
  | "ambassadors.create_campaigns"
  | "ambassadors.edit_campaigns"
  | "ambassadors.pause_campaigns"
  | "ambassadors.remove_participants"
  | "ambassadors.view_conversions"
  | "ambassadors.view_payouts"
  | "ambassadors.approve_rewards"
  | "ambassadors.reject_rewards"
  | "ambassadors.mark_rewards_paid"
  | "ambassadors.reverse_rewards"
  | "ambassadors.export";

export type HostTeamPermissions = Record<HostTeamPermissionKey, boolean>;

export type HostTeamMember = {
  id: string;
  host_id: string;
  user_id: string | null;
  role: string;
  role_label: string;
  status: string;
  /** Null for username invites — host never sees private account email. */
  invited_email: string | null;
  invite_method?: "email" | "username";
  invited_username?: string | null;
  avatar_url?: string | null;
  permissions: HostTeamPermissions;
  scope: "host_wide" | "selected_events";
  scoped_event_ids: string[];
  display_name: string | null;
  invite_expires_at: string | null;
  invited_at: string | null;
  accepted_at: string | null;
  suspended_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type HostTeamInvitePreview = {
  host_display_name: string;
  role: string;
  role_label: string;
  invite_method?: "email" | "username" | string;
  invited_email_hint: string;
  expires_at: string | null;
  status: string;
  already_accepted: boolean;
};

export type HostTeamAuditItem = {
  id: string;
  action: string;
  action_label?: string | null;
  actor_user_id: string | null;
  actor_label?: string | null;
  target_user_id?: string | null;
  target_label?: string | null;
  resource_type: string | null;
  resource_id: string | null;
  entity_type?: string | null;
  entity_id?: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
  source?: string | null;
};

export type HostBankAccount = {
  id: string;
  host_id: string;
  label: string;
  bank_name: string;
  account_name: string;
  account_number_last4: string;
  currency: string;
  status: string;
  is_default: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type HostVerification = {
  id: string;
  host_id: string;
  status: string;
  notes: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  host_display_name?: string | null;
  host_slug?: string | null;
  host_status?: string | null;
  owner_user_id?: string | null;
  owner_full_name?: string | null;
  owner_email?: string | null;
  events_count?: number;
};

export type EventTemplate = {
  id: string;
  host_id: string;
  name: string;
  description: string | null;
  payload: Record<string, unknown>;
  status: string;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};
