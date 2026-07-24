"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { RequireHostTeamManage } from "@/components/hosts/RequireHostTeamManage";
import { HostTeamSubnav } from "@/components/hosts/team/HostTeamSubnav";
import { TeamDeskQuickSetup } from "@/components/hosts/team/TeamDeskQuickSetup";
import { TeamEventScopePicker } from "@/components/hosts/team/TeamEventScopePicker";
import { TeamPermissionToggles } from "@/components/hosts/team/TeamPermissionToggles";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  Input,
  SectionHeader,
  Select,
  SkeletonLoader,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { fetchMyEvents } from "@/lib/events-api";
import { memberLabel } from "@/lib/host-team-helpers";
import {
  EMPTY_TEAM_PERMISSIONS,
  OWNER_ONLY_PERMISSION_KEYS,
  TEAM_ROLE_OPTIONS,
  defaultScopeForRole,
  mergePermissions,
  permissionsForRole,
  type TeamScope,
} from "@/lib/host-team-roles";
import { useUnsavedChanges } from "@/lib/hooks/useUnsavedChanges";
import {
  archiveHostTeamMember,
  fetchHostTeamMember,
  resendHostTeamInvite,
  restoreHostTeamMember,
  suspendHostTeamMember,
  updateHostTeamPermissions,
} from "@/lib/hosts-lifecycle-api";
import type { EventItem } from "@/lib/types/events";
import type {
  HostTeamMember,
  HostTeamPermissionKey,
  HostTeamPermissions,
} from "@/lib/types/lifecycle";

export default function HostTeamMemberDetailPage() {
  const params = useParams<{ id: string }>();
  const toast = useToast();
  const { active, isOwner } = useHostWorkspace();
  const hostId = active?.host_id ?? null;
  const [member, setMember] = useState<HostTeamMember | null>(null);
  const [role, setRole] = useState("scanner");
  const [roleLabel, setRoleLabel] = useState("");
  const [scope, setScope] = useState<TeamScope>("selected_events");
  const [scopedEventIds, setScopedEventIds] = useState<string[]>([]);
  const [hostEvents, setHostEvents] = useState<EventItem[]>([]);
  const [perms, setPerms] = useState<HostTeamPermissions>(EMPTY_TEAM_PERMISSIONS);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyLifecycle, setBusyLifecycle] = useState(false);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const row = await fetchHostTeamMember(params.id, hostId);
        if (!alive) return;
        setMember(row);
        setRole(row.role || "scanner");
        setRoleLabel(row.role_label);
        setScope(row.scope || defaultScopeForRole(row.role));
        setScopedEventIds((row.scoped_event_ids || []).map(String));
        setPerms(mergePermissions(row.permissions));
      } catch (err) {
        if (alive) {
          setError(err instanceof ApiError ? err.detail : "Failed to load member");
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [params.id, hostId]);

  useEffect(() => {
    void fetchMyEvents()
      .then(setHostEvents)
      .catch(() => setHostEvents([]));
  }, [hostId]);

  const dirty = useMemo(() => {
    if (!member) return false;
    const p = mergePermissions(member.permissions);
    const memberIds = (member.scoped_event_ids || []).map(String).sort().join(",");
    const nextIds = [...scopedEventIds].sort().join(",");
    return (
      role !== member.role ||
      roleLabel !== member.role_label ||
      scope !== member.scope ||
      memberIds !== nextIds ||
      (Object.keys(EMPTY_TEAM_PERMISSIONS) as HostTeamPermissionKey[]).some(
        (k) => perms[k] !== p[k],
      )
    );
  }, [member, role, roleLabel, scope, scopedEventIds, perms]);

  useUnsavedChanges(dirty);

  async function reload() {
    const row = await fetchHostTeamMember(params.id, hostId);
    setMember(row);
    setRole(row.role || "scanner");
    setRoleLabel(row.role_label);
    setScope(row.scope || defaultScopeForRole(row.role));
    setScopedEventIds((row.scoped_event_ids || []).map(String));
    setPerms(mergePermissions(row.permissions));
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!member) return;
    setSaving(true);
    setError(null);
    try {
      await updateHostTeamPermissions(
        member.id,
        {
          role,
          role_label: roleLabel.trim() || role,
          permissions: perms,
          scope,
          scoped_event_ids:
            scope === "selected_events" ? scopedEventIds : [],
        },
        hostId,
      );
      toast.push({ title: "Permissions saved", tone: "success" });
      await reload();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Save failed";
      setError(detail);
      toast.push({ title: "Save failed", description: detail, tone: "danger" });
    } finally {
      setSaving(false);
    }
  }

  async function onRemove() {
    if (!member) return;
    setBusyLifecycle(true);
    setError(null);
    try {
      await archiveHostTeamMember(member.id, hostId);
      toast.push({ title: "Member removed", tone: "success" });
      await reload();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Remove failed";
      setError(detail);
      toast.push({ title: "Remove failed", description: detail, tone: "danger" });
    } finally {
      setBusyLifecycle(false);
    }
  }

  async function onRestore() {
    if (!member) return;
    setBusyLifecycle(true);
    setError(null);
    try {
      await restoreHostTeamMember(member.id, hostId);
      toast.push({ title: "Member restored", tone: "success" });
      await reload();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Restore failed";
      setError(detail);
      toast.push({ title: "Restore failed", description: detail, tone: "danger" });
    } finally {
      setBusyLifecycle(false);
    }
  }

  async function onSuspend() {
    if (!member) return;
    setBusyLifecycle(true);
    setError(null);
    try {
      await suspendHostTeamMember(member.id, hostId);
      toast.push({ title: "Member suspended", tone: "success" });
      await reload();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Suspend failed";
      setError(detail);
      toast.push({ title: "Suspend failed", description: detail, tone: "danger" });
    } finally {
      setBusyLifecycle(false);
    }
  }

  async function onResend() {
    if (!member) return;
    setBusyLifecycle(true);
    setError(null);
    try {
      await resendHostTeamInvite(member.id, hostId);
      toast.push({ title: "Invite resent", tone: "success" });
      await reload();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Resend failed";
      setError(detail);
      toast.push({ title: "Resend failed", description: detail, tone: "danger" });
    } finally {
      setBusyLifecycle(false);
    }
  }

  const title = member ? memberLabel(member) : "Team member";

  function toggle(key: HostTeamPermissionKey) {
    if (!isOwner && OWNER_ONLY_PERMISSION_KEYS.includes(key)) return;
    setPerms((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  const archived = member?.archived_at != null;
  const pending = member?.status === "pending";

  return (
    <RequireHostTeamManage>
      <DashboardShell
        tone="soft"
        eyebrow="Host Team"
        title={title}
        description="Edit role, status, permissions, and event scope. Scanner/merch stay easy with quick desk presets."
        actions={
          <Link href="/host/team/members">
            <Button variant="ghost">Back to members</Button>
          </Link>
        }
      >
        <HostTeamSubnav />

        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {loading && !error ? <SkeletonLoader lines={5} /> : null}

        {!loading && member ? (
          <div className="space-y-6">
            <Card className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                {member.avatar_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={member.avatar_url}
                    alt=""
                    className="h-12 w-12 rounded-full object-cover"
                  />
                ) : null}
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={member.status} />
                  {archived ? <StatusBadge status="archived" /> : null}
                </div>
              </div>
              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                    {member.invite_method === "username" || member.invited_username
                      ? "Username"
                      : "Email"}
                  </dt>
                  <dd className="mt-1 font-semibold text-foreground">
                    {member.invite_method === "username" || member.invited_username
                      ? member.invited_username || "—"
                      : member.invited_email || "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                    Invited
                  </dt>
                  <dd className="mt-1 text-muted-foreground">
                    {formatDateTime(member.invited_at || member.created_at)}
                  </dd>
                </div>
                {member.accepted_at ? (
                  <div>
                    <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                      Accepted
                    </dt>
                    <dd className="mt-1 text-muted-foreground">
                      {formatDateTime(member.accepted_at)}
                    </dd>
                  </div>
                ) : null}
              </dl>
            </Card>

            <Card className="max-w-2xl space-y-4">
              <SectionHeader
                title="Role & permissions"
                description="Quick desk presets for scanner/merch, or pick any role and edit toggles."
              />
              <form className="space-y-4" onSubmit={onSave}>
                <TeamDeskQuickSetup
                  role={role}
                  scope={scope}
                  perms={perms}
                  disabled={archived}
                  onApply={({ role: nextRole, scope: nextScope, perms: nextPerms }) => {
                    setRole(nextRole);
                    const label =
                      TEAM_ROLE_OPTIONS.find((o) => o.value === nextRole)?.label.split(
                        " — ",
                      )[0] || nextRole;
                    setRoleLabel(label);
                    setScope(nextScope);
                    if (!isOwner) {
                      for (const key of OWNER_ONLY_PERMISSION_KEYS) {
                        nextPerms[key] = perms[key];
                      }
                    }
                    setPerms(nextPerms);
                  }}
                />

                <Select
                  label="Role preset"
                  value={role}
                  onChange={(e) => {
                    const next = e.target.value;
                    setRole(next);
                    const label =
                      TEAM_ROLE_OPTIONS.find((o) => o.value === next)?.label.split(
                        " — ",
                      )[0] || next;
                    setRoleLabel(label);
                    setScope(defaultScopeForRole(next));
                    const nextPerms = permissionsForRole(next);
                    if (!isOwner) {
                      for (const key of OWNER_ONLY_PERMISSION_KEYS) {
                        nextPerms[key] = perms[key];
                      }
                    }
                    setPerms(nextPerms);
                  }}
                  disabled={archived}
                >
                  {TEAM_ROLE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </Select>
                <Input
                  label="Display label"
                  value={roleLabel}
                  onChange={(e) => setRoleLabel(e.target.value)}
                  placeholder="Door lead, merch desk…"
                  disabled={archived}
                />

                <TeamEventScopePicker
                  scope={scope}
                  onScopeChange={setScope}
                  eventIds={scopedEventIds}
                  onEventIdsChange={setScopedEventIds}
                  events={hostEvents}
                  disabled={archived}
                />

                <fieldset className="space-y-2">
                  <legend className="text-sm font-semibold text-foreground">
                    Permission toggles
                  </legend>
                  <TeamPermissionToggles
                    perms={perms}
                    onToggle={toggle}
                    isOwner={isOwner}
                    disabled={archived}
                  />
                </fieldset>

                <div className="flex flex-wrap gap-2">
                  <Button
                    type="submit"
                    disabled={!dirty || saving || archived}
                  >
                    {saving ? "Saving…" : "Save changes"}
                  </Button>
                </div>
              </form>
            </Card>

            <Card className="max-w-2xl space-y-4">
              <SectionHeader
                title="Lifecycle"
                description="Suspend access, remove from the team, or resend a pending invite."
              />
              <div className="flex flex-wrap gap-2">
                {pending ? (
                  <Button
                    variant="secondary"
                    disabled={busyLifecycle}
                    onClick={() => void onResend()}
                  >
                    Resend invite
                  </Button>
                ) : null}
                {member.status === "active" && !archived ? (
                  <ConfirmAction
                    label="Suspend"
                    title="Suspend team member?"
                    description={`Suspend ${title}. Access stops until restored.`}
                    confirmLabel="Suspend"
                    disabled={busyLifecycle}
                    busy={busyLifecycle}
                    onConfirm={() => onSuspend()}
                  />
                ) : null}
                {archived ? (
                  <ConfirmAction
                    label="Restore member"
                    title="Restore team member?"
                    description={`Restore access for ${title}.`}
                    confirmLabel="Restore"
                    disabled={busyLifecycle || !member.user_id}
                    busy={busyLifecycle}
                    onConfirm={() => onRestore()}
                  />
                ) : !pending ? (
                  <ConfirmAction
                    label="Remove"
                    title="Remove team member?"
                    description={`Remove ${title} from your Pàdéyá host team.`}
                    confirmLabel="Remove"
                    tone="danger"
                    disabled={busyLifecycle}
                    busy={busyLifecycle}
                    onConfirm={() => onRemove()}
                  />
                ) : null}
              </div>
            </Card>
          </div>
        ) : null}

        {!loading && !member && !error ? (
          <Alert tone="warning" title="Not found">
            This team member could not be loaded.
          </Alert>
        ) : null}
      </DashboardShell>
    </RequireHostTeamManage>
  );
}
