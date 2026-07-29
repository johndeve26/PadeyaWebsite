"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Input,
  Select,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import {
  fetchAdminTeamRoles,
  inviteAdminTeamMember,
  type AdminTeamRole,
} from "@/lib/admin-team/api";
import { ApiError } from "@/lib/api";

export default function AdminTeamInvitePage() {
  const toast = useToast();
  const [roles, setRoles] = useState<AdminTeamRole[]>([]);
  const [email, setEmail] = useState("");
  const [roleId, setRoleId] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [doneHref, setDoneHref] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      void (async () => {
        try {
          const data = await fetchAdminTeamRoles();
          if (cancelled) return;
          setRoles(data.roles);
          const support = data.roles.find((r) => r.system_key === "support");
          setRoleId(support?.id || data.roles[0]?.id || "");
        } catch (err) {
          if (!cancelled) {
            setError(
              err instanceof ApiError ? err.message : "Failed to load roles",
            );
          }
        } finally {
          if (!cancelled) setLoading(false);
        }
      })();
    });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result = await inviteAdminTeamMember({
        email: email.trim(),
        admin_role_id: roleId || undefined,
      });
      toast.push({
        title: result.status === "provisioned" ? "Member added" : "Invite sent",
        description:
          result.status === "provisioned"
            ? "Existing account provisioned — invite email sent."
            : `Invite email sent to ${result.email_hint}`,
        tone: "success",
      });
      setDoneHref(
        result.member?.id ? `/admin/team/${result.member.id}` : "/admin/team",
      );
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Invite failed";
      setError(message);
      toast.push({ title: "Invite failed", description: message, tone: "danger" });
    } finally {
      setSubmitting(false);
    }
  }

  if (doneHref) {
    return (
      <DashboardShell tone="soft" eyebrow="Admin · Team" title="Invite sent">
        <Alert tone="success">
          Invite email sent. They can accept from their inbox (or sign in if
          they already have an account).
        </Alert>
        <div className="mt-4">
          <Link href={doneHref}>
            <Button>Continue</Button>
          </Link>
        </div>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Team"
      title="Invite member"
      description="Invite by email and assign a role or custom team."
      actions={
        <Link href="/admin/team">
          <Button variant="secondary" size="sm">
            Back
          </Button>
        </Link>
      }
    >
      {loading ? (
        <SkeletonLoader lines={5} />
      ) : (
        <form onSubmit={onSubmit} className="mx-auto max-w-lg space-y-5">
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <Input
            label="Email"
            id="email"
            type="email"
            required
            value={email}
            onChange={(ev) => setEmail(ev.target.value)}
            placeholder="colleague@padeya.com"
          />
          <Select
            label="Role / team"
            id="role"
            required
            value={roleId}
            onChange={(ev) => setRoleId(ev.target.value)}
          >
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.is_system ? r.name : `${r.name} (custom)`}
              </option>
            ))}
          </Select>
          <Button type="submit" disabled={submitting || !roleId}>
            {submitting ? "Sending…" : "Send invite"}
          </Button>
        </form>
      )}
    </DashboardShell>
  );
}
