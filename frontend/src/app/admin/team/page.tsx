"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  EmptyState,
  SectionHeader,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import {
  fetchAdminTeam,
  type AdminPendingInvite,
  type AdminTeamMember,
} from "@/lib/admin-team/api";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

export default function AdminTeamPage() {
  const toast = useToast();
  const [members, setMembers] = useState<AdminTeamMember[]>([]);
  const [invites, setInvites] = useState<AdminPendingInvite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAdminTeam();
      setMembers(data.members);
      setInvites(data.pending_invites);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to load team";
      setError(message);
      toast.push({ title: "Could not load team", description: message, tone: "danger" });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) void load();
    });
    return () => {
      cancelled = true;
    };
  }, [load]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Team"
      description="Invite internal staff, assign roles, and review access."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/team/roles">
            <Button variant="secondary" size="sm">
              Roles
            </Button>
          </Link>
          <Link href="/admin/team/invite">
            <Button size="sm">Invite member</Button>
          </Link>
        </div>
      }
    >
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {loading ? (
        <SkeletonLoader lines={6} />
      ) : (
        <div className="space-y-10">
          <section className="space-y-4">
            <SectionHeader title="Members" description="Active and disabled staff." />
            {members.length === 0 ? (
              <EmptyState
                title="No team members yet"
                description="Invite support, finance, or custom-role staff."
                action={
                  <Link href="/admin/team/invite">
                    <Button size="sm">Invite member</Button>
                  </Link>
                }
              />
            ) : (
              <ul className="divide-y divide-border border-y border-border">
                {members.map((m) => (
                  <li key={m.id} className="flex flex-wrap items-center justify-between gap-3 py-4">
                    <div>
                      <p className="font-semibold text-heading">
                        {m.user?.full_name || m.user?.email || m.user_id}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {m.user?.email} · {m.role?.name || "No role"} · {m.status}
                      </p>
                    </div>
                    <Link href={`/admin/team/${m.id}`}>
                      <Button variant="secondary" size="sm">
                        View
                      </Button>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-4">
            <SectionHeader
              title="Pending invites"
              description="Invites waiting for an account."
            />
            {invites.length === 0 ? (
              <p className="text-sm text-muted-foreground">No pending invites.</p>
            ) : (
              <ul className="divide-y divide-border border-y border-border">
                {invites.map((inv) => (
                  <li key={inv.id} className="py-3 text-sm">
                    <span className="font-medium text-heading">{inv.email_hint}</span>
                    {" · "}
                    {inv.role?.name || "Role"}
                    {inv.expires_at
                      ? ` · expires ${formatDateTime(inv.expires_at)}`
                      : null}
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
