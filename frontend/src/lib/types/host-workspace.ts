import type { HostTeamPermissions } from "@/lib/types/lifecycle";

export type HostWorkspaceKind = "owner" | "team_member" | "event_staff";

export type HostWorkspacePermissions = HostTeamPermissions;

export type HostWorkspace = {
  host_id: string;
  display_name: string;
  slug: string;
  kind: HostWorkspaceKind;
  role: string;
  role_label: string;
  permissions: HostWorkspacePermissions;
  scope: "host_wide" | "selected_events";
  scoped_event_ids: string[];
  membership_id: string | null;
  is_owner: boolean;
  is_active?: boolean;
};

export type HostDeskEvent = {
  id: string;
  title: string;
  slug: string;
  status: string;
  start_datetime: string;
  staff_check_in_path: string;
  host_check_in_path: string;
};
