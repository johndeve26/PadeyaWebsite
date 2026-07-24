import type { HostTeamMember, HostTeamPermissions } from "@/lib/types/lifecycle";

export function memberLabel(row: HostTeamMember): string {
  if (row.invite_method === "username" || row.invited_username) {
    return (
      row.display_name ||
      row.invited_username ||
      row.user_id ||
      "Team member"
    );
  }
  return row.display_name || row.invited_email || row.user_id || "Team member";
}

/** Primary invitee line for host UI (never prefer hidden email for username invites). */
export function inviteePrimaryLabel(row: HostTeamMember): string {
  if (row.invite_method === "username" || row.invited_username) {
    return row.invited_username || row.display_name || "Pàdéyá user";
  }
  return row.invited_email || row.display_name || memberLabel(row);
}

export function isPendingInvite(row: HostTeamMember): boolean {
  return row.status === "pending" || row.status === "expired";
}

export function isActiveMember(row: HostTeamMember): boolean {
  return (
    !isPendingInvite(row) &&
    row.archived_at == null &&
    row.status !== "removed"
  );
}

export function deskAccessSummary(perms: HostTeamPermissions | null | undefined): string {
  const parts: string[] = [];
  if (perms?.["tickets.scan_qr"] || perms?.["tickets.check_in"]) {
    parts.push("Ticket desk");
  }
  if (perms?.["merch.scan_pickup_qr"] || perms?.["merch.mark_picked_up"]) {
    parts.push("Merch desk");
  }
  if (perms?.["team.invite"]) parts.push("Team");
  return parts.join(" · ") || "—";
}

export function scopeLabel(scope: string | undefined): string {
  return scope === "selected_events" ? "Selected events" : "Host-wide";
}

const AUDIT_ACTION_LABELS: Record<string, string> = {
  "hosts.team_invite": "Invite sent",
  "hosts.team_accept": "Invite accepted",
  "hosts.team_member_added": "Member added",
  "hosts.team_decline": "Invite declined",
  "hosts.team_revoke": "Invite revoked",
  "hosts.team_resend": "Invite resent",
  "hosts.team_suspend": "Member suspended",
  "hosts.team_permissions_update": "Permissions changed",
  "hosts.team_scope_update": "Scope changed",
  "hosts.team_finance_permission_grant": "Payout/finance permission grant",
  "hosts.team_permission_denied": "Denied permission attempt",
  "hosts.team_create": "Member created",
  "hosts.team_update": "Member updated",
  "hosts.team_archive": "Member removed",
  "hosts.team_remove": "Member removed",
  "hosts.team_restore": "Member restored",
  "tickets.scan": "Ticket scanned",
  "merch.scan_pickup": "Merch pickup scanned",
  "merch.pickup_scan": "Merch pickup scanned",
};

export function auditActionLabel(
  action: string,
  actionLabel?: string | null,
): string {
  if (actionLabel) return actionLabel;
  if (AUDIT_ACTION_LABELS[action]) return AUDIT_ACTION_LABELS[action];
  return action.replace(/^hosts\./, "").replace(/[._]/g, " ");
}

/** Keys that must never appear in audit UI even if the API returned them. */
const UNSAFE_META_KEYS = new Set([
  "token",
  "token_hash",
  "raw_token",
  "invite_token",
  "password",
  "secret",
  "api_key",
  "authorization",
  "account_number",
  "paystack_reference",
  "payment_reference",
  "payment_ref",
  "provider_reference",
  "authorization_code",
  "access_code",
  "webhook_secret",
  "host_id",
]);

export function formatAuditMetadata(
  details: Record<string, unknown> | null | undefined,
): string {
  if (!details) return "";
  const hideEmail = details.invite_method === "username";
  const parts: string[] = [];
  for (const [key, value] of Object.entries(details)) {
    const keyL = key.toLowerCase();
    if (UNSAFE_META_KEYS.has(keyL)) continue;
    if (hideEmail && keyL === "invited_email") continue;
    if (
      keyL.includes("token") ||
      keyL.includes("secret") ||
      keyL.includes("password") ||
      keyL.includes("paystack") ||
      keyL.includes("payment_ref") ||
      keyL.includes("account_number")
    ) {
      continue;
    }
    if (value == null || value === "") continue;
    if (typeof value === "object") continue;
    parts.push(`${key.replace(/_/g, " ")}: ${String(value)}`);
  }
  return parts.join(" · ");
}

export function auditEntityLabel(item: {
  entity_type?: string | null;
  entity_id?: string | null;
  resource_type?: string | null;
  resource_id?: string | null;
}): string {
  const type = item.entity_type || item.resource_type;
  const id = item.entity_id || item.resource_id;
  if (!type && !id) return "—";
  if (type && id) {
    const short =
      id.length > 12 ? `${id.slice(0, 8)}…` : id;
    return `${type.replace(/_/g, " ")} · ${short}`;
  }
  return (type || id || "—").replace(/_/g, " ");
}
