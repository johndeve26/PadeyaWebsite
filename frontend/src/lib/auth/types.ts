export type AuthTokens = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type ImpersonationDurationMinutes = 15 | 30 | 60;

export type ImpersonationInfo = {
  active: boolean;
  is_impersonating?: boolean;
  impersonation_id: string;
  actual_user_id?: string;
  actor_admin_id?: string;
  impersonator_id: string;
  impersonator_email?: string | null;
  impersonator_full_name?: string | null;
  target_user_id: string;
  target_email?: string | null;
  target_full_name?: string | null;
  reason?: string | null;
  support_ticket_id?: string | null;
  duration_minutes?: number | null;
  started_at?: string | null;
  expires_at?: string | null;
  scopes?: string[];
  pack?: string | null;
};

export type UserSuspensionPublic = {
  id: string;
  status: string;
  reason_category: string;
  reason_category_label: string;
  starts_at: string;
  ends_at: string | null;
  duration_label: string;
};

export type User = {
  id: string;
  email: string;
  full_name: string;
  username?: string | null;
  is_active: boolean;
  is_verified: boolean;
  roles: string[];
  permissions: string[];
  created_at: string;
  /** Active restriction keys only — never admin reason/internal_note. */
  account_restrictions?: string[];
  restriction_keys?: string[];
  account_status?: string;
  ambassadors_blocked?: boolean;
  under_review?: boolean;
  /** Public suspension summary for appeal/status surfaces — never internal notes. */
  suspension?: UserSuspensionPublic | null;
  impersonation?: ImpersonationInfo | null;
};

export type ImpersonationStartInput = {
  userId: string;
  reason: string;
  supportTicketId?: string;
  durationMinutes?: ImpersonationDurationMinutes;
};

export type ImpersonationStartResponse = {
  impersonation_id: string;
  target_user_id: string;
  expires_at: string;
  redirect_to: string;
  access_token: string;
  token_type: string;
  scopes?: string[];
  pack?: string | null;
};

export type ImpersonationEndResponse = {
  ended: boolean;
  return_to: string;
};

export type ImpersonationStatusResponse = {
  is_impersonating: boolean;
  impersonation_id?: string | null;
  actual_user_id?: string | null;
  actor_admin_id?: string | null;
  target_user_id?: string | null;
  reason?: string | null;
  support_ticket_id?: string | null;
  started_at?: string | null;
  expires_at?: string | null;
  impersonator_email?: string | null;
  impersonator_full_name?: string | null;
  target_email?: string | null;
  target_full_name?: string | null;
  scopes?: string[];
  pack?: string | null;
};

export type ImpersonationHistoryItem = {
  id: string;
  actor_admin_id: string;
  started_by: string;
  started_by_email?: string | null;
  target_user_id: string;
  reason: string;
  support_ticket_id?: string | null;
  started_at: string;
  ended_at?: string | null;
  expires_at: string;
  status: string;
  scopes?: string[];
  pack?: string | null;
};

export type ImpersonationTokenResponse = ImpersonationStartResponse;

export type AuthRole =
  | "buyer"
  | "host"
  | "host_staff"
  | "support_agent"
  | "finance_admin"
  | "super_admin";
