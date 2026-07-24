"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  ConfirmAction,
  Input,
  Select,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import {
  disableAdminTeamMember,
  fetchAdminTeamMember,
  fetchAdminTeamRoles,
  forceLogoutAdminTeamMember,
  updateAdminTeamMember,
  type AdminTeamAuditItem,
  type AdminTeamMember,
  type AdminTeamRole,
} from "@/lib/admin-team/api";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

export default function AdminTeamMemberDetailPage() {
  const params = useParams();
  const memberId = String(params.memberId || "");
  const toast = useToast();
  const [member, setMember] = useState<AdminTeamMember | null>(null);
  const [audit, setAudit] = useState<AdminTeamAuditItem[]>([]);
  const [roles, setRoles] = useState<AdminTeamRole[]>([]);
  const [roleId, setRoleId] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!memberId) return;
    setLoading(true);
    setError(null);
    try {
      const [detail, roleData] = await Promise.all([
        fetchAdminTeamMember(memberId),
        fetchAdminTeamRoles(),
      ]);
      setMember(detail.member);
      setAudit(detail.audit);
      setRoles(roleData.roles);
      setRoleId(detail.member.role?.id || "");
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to load member";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [memberId]);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) void load();
    });
    return () => {
      cancelled = true;
    };
  }, [load]);

  async function saveRole() {
    if (!member) return;
    setBusy(true);
    try {
      const updated = await updateAdminTeamMember(member.id, {
        admin_role_id: roleId,
      });
      setMember(updated);
      toast.push({ title: "Role updated", tone: "success" });
      await load();
    } catch (err) {
      toast.push({
        title: "Update failed",
        description: err instanceof ApiError ? err.message : "Error",
        tone: "danger",
      });
    } finally {
      setBusy(false);
    }
  }

  async function onDisable(remove: boolean) {
    if (!member) return;
    setBusy(true);
    try {
      const updated = await disableAdminTeamMember(member.id, {
        reason: reason || undefined,
        remove,
      });
      setMember(updated);
      toast.push({
        title: remove ? "Member removed" : "Access disabled",
        tone: "success",
      });
      await load();
    } catch (err) {
      toast.push({
        title: "Action failed",
        description: err instanceof ApiError ? err.message : "Error",
        tone: "danger",
      });
    } finally {
      setBusy(false);
    }
  }

  async function onForceLogout() {
    if (!member) return;
    setBusy(true);
    try {
      const result = await forceLogoutAdminTeamMember(member.id, {
        reason: reason || undefined,
      });
      toast.push({
        title: "Sessions revoked",
        description: `${result.revoked_count} session(s)`,
        tone: "success",
      });
      await load();
    } catch (err) {
      toast.push({
        title: "Force logout failed",
        description: err instanceof ApiError ? err.message : "Error",
        tone: "danger",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Team"
      title={member?.user?.full_name || member?.user?.email || "Team member"}
      description="Role, access controls, and activity."
      actions={
        <Link href="/admin/team">
          <Button variant="secondary" size="sm">
            Back
          </Button>
        </Link>
      }
    >
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {loading || !member ? (
        <SkeletonLoader lines={8} />
      ) : (
        <div className="space-y-10">
          <section className="space-y-2">
            <p className="text-sm text-muted-foreground">{member.user?.email}</p>
            <p className="text-sm">
              Status: <span className="font-medium">{member.status}</span>
              {member.role ? ` · ${member.role.name}` : null}
            </p>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-heading">Change role</h2>
            <Select
              label="Role"
              value={roleId}
              onChange={(ev) => setRoleId(ev.target.value)}
              disabled={busy}
            >
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </Select>
            <Button onClick={() => void saveRole()} disabled={busy || !roleId}>
              Save role
            </Button>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-heading">Access actions</h2>
            <Input
              label="Reason (optional)"
              value={reason}
              onChange={(ev) => setReason(ev.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => void onForceLogout()}
              >
                Force logout
              </Button>
              <ConfirmAction
                label="Disable"
                title="Disable access?"
                description="Removes admin roles and revokes sessions."
                confirmLabel="Disable"
                disabled={busy}
                onConfirm={() => onDisable(false)}
              />
              <ConfirmAction
                label="Remove"
                title="Remove from team?"
                description="Marks the member removed and strips admin access."
                confirmLabel="Remove"
                tone="danger"
                disabled={busy}
                onConfirm={() => onDisable(true)}
              />
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-heading">Permissions</h2>
            {member.permissions.length === 0 ? (
              <p className="text-sm text-muted-foreground">No permissions.</p>
            ) : (
              <ul className="columns-1 gap-2 text-sm sm:columns-2">
                {member.permissions.map((code) => (
                  <li key={code} className="break-inside-avoid text-muted-foreground">
                    {code}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-heading">Activity / audit</h2>
            {audit.length === 0 ? (
              <p className="text-sm text-muted-foreground">No audit entries.</p>
            ) : (
              <ul className="divide-y divide-border border-y border-border">
                {audit.map((row) => (
                  <li key={row.id} className="py-3 text-sm">
                    <p className="font-medium text-heading">{row.action}</p>
                    <p className="text-muted-foreground">
                      {row.created_at ? formatDateTime(row.created_at) : "—"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}
