"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { RequireHostTeamManage } from "@/components/hosts/RequireHostTeamManage";
import { HostTeamSubnav } from "@/components/hosts/team/HostTeamSubnav";
import { TeamInviteModal } from "@/components/hosts/team/TeamInviteModal";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  SectionHeader,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { fetchMyEvents } from "@/lib/events-api";
import {
  auditActionLabel,
  deskAccessSummary,
  isPendingInvite,
  memberLabel,
  scopeLabel,
} from "@/lib/host-team-helpers";
import { TEAM_ROLE_OPTIONS } from "@/lib/host-team-roles";
import {
  fetchHostTeamAudit,
  fetchHostTeamInvites,
  fetchHostTeamMembers,
} from "@/lib/hosts-lifecycle-api";
import type { EventItem } from "@/lib/types/events";
import type { HostTeamAuditItem, HostTeamMember } from "@/lib/types/lifecycle";

export default function HostTeamPage() {
  const toast = useToast();
  const { active, isOwner } = useHostWorkspace();
  const hostId = active?.host_id ?? null;
  const [members, setMembers] = useState<HostTeamMember[]>([]);
  const [invites, setInvites] = useState<HostTeamMember[]>([]);
  const [audit, setAudit] = useState<HostTeamAuditItem[]>([]);
  const [hostEvents, setHostEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteRole, setInviteRole] = useState("scanner");

  async function load() {
    const [m, i, logs] = await Promise.all([
      fetchHostTeamMembers(false, hostId),
      fetchHostTeamInvites(false, hostId),
      fetchHostTeamAudit(12, hostId),
    ]);
    setMembers(m);
    setInvites(i);
    setAudit(logs);
  }

  useEffect(() => {
    if (!hostId) return;
    let alive = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (alive) {
          setError(err instanceof ApiError ? err.detail : "Failed to load team");
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload when workspace changes
  }, [hostId]);

  useEffect(() => {
    if (!hostId) return;
    void fetchMyEvents()
      .then(setHostEvents)
      .catch(() => setHostEvents([]));
  }, [hostId]);

  function openInvite(role = "scanner") {
    setInviteRole(role);
    setInviteOpen(true);
  }

  const previewMembers = members.slice(0, 5);
  const previewInvites = invites.slice(0, 5);
  const assignmentRows = members.filter(
    (m) =>
      !isPendingInvite(m) &&
      m.scope === "selected_events" &&
      (m.scoped_event_ids?.length ?? 0) > 0,
  );

  return (
    <RequireHostTeamManage>
      <DashboardShell
        tone="soft"
        eyebrow="Manage"
        title="Host Team"
        description="Invite collaborators, set roles and desk scope, and review team activity."
        actions={
          <Button type="button" onClick={() => openInvite("scanner")}>
            Invite team member
          </Button>
        }
      >
        <HostTeamSubnav />

        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        <div className="mb-8 grid gap-3 sm:grid-cols-2">
          <Card className="space-y-3 p-4">
            <SectionHeader
              title="Door & pickup staff"
              description="Fast presets for ticket scanners and merch desk."
            />
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                onClick={() => openInvite("scanner")}
              >
                Invite scanner
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => openInvite("merch_staff")}
              >
                Invite merch staff
              </Button>
            </div>
          </Card>
          <Card className="space-y-3 p-4">
            <SectionHeader
              title="Roles & permissions"
              description={`${TEAM_ROLE_OPTIONS.length} presets — every toggle stays editable after invite.`}
            />
            <ul className="space-y-1 text-sm text-muted-foreground">
              {TEAM_ROLE_OPTIONS.slice(0, 4).map((opt) => (
                <li key={opt.value}>
                  <span className="font-semibold text-foreground">
                    {opt.label.split(" — ")[0]}
                  </span>
                  {" — "}
                  {opt.label.split(" — ")[1]}
                </li>
              ))}
            </ul>
            <p className="text-xs text-muted-foreground">
              Scanner/merch default to selected events. Payout settings stay
              owner-only unless explicitly granted.
            </p>
          </Card>
        </div>

        <section className="mb-10 space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <SectionHeader
              title="Team members"
              description={
                loading
                  ? "Loading…"
                  : `${members.length} active or suspended member${members.length === 1 ? "" : "s"}.`
              }
            />
            <Link href="/host/team/members">
              <Button variant="secondary" size="sm">
                View all members
              </Button>
            </Link>
          </div>
          {!loading && members.length === 0 ? (
            <EmptyState
              title="No members yet"
              description="Invite someone to help run doors, merch, or events."
            />
          ) : (
            <ul className="divide-y divide-border rounded-md border border-border">
              {previewMembers.map((row) => (
                <li
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-foreground">
                      {memberLabel(row)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {row.role_label || row.role} · {scopeLabel(row.scope)} ·{" "}
                      {deskAccessSummary(row.permissions)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={row.status} />
                    <Link href={`/host/team/${row.id}`}>
                      <Button size="sm" variant="ghost">
                        Edit
                      </Button>
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="mb-10 space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <SectionHeader
              title="Pending invites"
              description={
                loading
                  ? "Loading…"
                  : `${invites.length} open invite${invites.length === 1 ? "" : "s"}.`
              }
            />
            <Link href="/host/team/invites">
              <Button variant="secondary" size="sm">
                Manage invites
              </Button>
            </Link>
          </div>
          {!loading && invites.length === 0 ? (
            <EmptyState
              title="No pending invites"
              description="Sent invites appear here until accepted, revoked, or expired."
            />
          ) : (
            <ul className="divide-y divide-border rounded-md border border-border">
              {previewInvites.map((row) => (
                <li
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-foreground">
                      {row.invited_username ||
                        row.invited_email ||
                        memberLabel(row)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {row.role_label || row.role} · expires{" "}
                      {row.invite_expires_at
                        ? formatDateTime(row.invite_expires_at)
                        : "—"}
                    </p>
                  </div>
                  <StatusBadge status={row.status} />
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="mb-10 space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <SectionHeader
              title="Event assignments"
              description="Members scoped to selected events. Assign more from each event’s Attendees desk."
            />
            <Link href="/host/events">
              <Button variant="secondary" size="sm">
                Open events
              </Button>
            </Link>
          </div>
          {assignmentRows.length === 0 ? (
            <EmptyState
              title="No event-scoped members yet"
              description="Invite scanner or merch staff and pick events in the invite modal."
            />
          ) : (
            <ul className="divide-y divide-border rounded-md border border-border">
              {assignmentRows.slice(0, 6).map((row) => (
                <li
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                >
                  <div>
                    <p className="font-semibold text-foreground">
                      {memberLabel(row)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {(row.scoped_event_ids || []).length} event
                      {(row.scoped_event_ids || []).length === 1 ? "" : "s"} ·{" "}
                      {row.role_label || row.role}
                    </p>
                  </div>
                  <Link href={`/host/team/${row.id}`}>
                    <Button size="sm" variant="ghost">
                      Edit scope
                    </Button>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <SectionHeader
              title="Audit log"
              description="Recent invite, member, permission, and desk activity."
            />
            <Link href="/host/team/audit-log">
              <Button variant="secondary" size="sm">
                Full audit log
              </Button>
            </Link>
          </div>
          {audit.length === 0 ? (
            <EmptyState
              title="No team activity yet"
              description="Actions on invites and members will show up here."
            />
          ) : (
            <Card className="space-y-0 p-0">
              <ul className="divide-y divide-border text-sm">
                {audit.map((item) => (
                  <li
                    key={item.id}
                    className="flex flex-wrap justify-between gap-2 px-4 py-2.5"
                  >
                    <div className="min-w-0 space-y-0.5">
                      <span className="font-medium text-foreground">
                        {auditActionLabel(item.action, item.action_label)}
                      </span>
                      <p className="text-xs text-muted-foreground">
                        {[item.actor_label, item.target_label]
                          .filter(Boolean)
                          .join(" → ") || "—"}
                      </p>
                    </div>
                    <span className="shrink-0 text-muted-foreground">
                      {formatDateTime(item.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </section>

        <TeamInviteModal
          open={inviteOpen}
          onClose={() => setInviteOpen(false)}
          hostId={hostId}
          isOwner={isOwner}
          events={hostEvents}
          initialRole={inviteRole}
          onInvited={load}
          onError={(detail) => {
            setError(detail);
            toast.push({
              title: "Could not send invite",
              description: detail,
              tone: "danger",
            });
          }}
          onSuccess={(description) =>
            toast.push({ title: "Invite sent", description, tone: "success" })
          }
        />
      </DashboardShell>
    </RequireHostTeamManage>
  );
}
