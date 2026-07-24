"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { RequireHostTeamManage } from "@/components/hosts/RequireHostTeamManage";
import { HostTeamSubnav } from "@/components/hosts/team/HostTeamSubnav";
import { TeamInviteModal } from "@/components/hosts/team/TeamInviteModal";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { fetchMyEvents } from "@/lib/events-api";
import {
  deskAccessSummary,
  inviteePrimaryLabel,
  memberLabel,
  scopeLabel,
} from "@/lib/host-team-helpers";
import {
  archiveHostTeamMember,
  fetchHostTeamMembers,
  restoreHostTeamMember,
  suspendHostTeamMember,
} from "@/lib/hosts-lifecycle-api";
import type { EventItem } from "@/lib/types/events";
import type { HostTeamMember } from "@/lib/types/lifecycle";

export default function HostTeamMembersPage() {
  const toast = useToast();
  const { active, isOwner } = useHostWorkspace();
  const hostId = active?.host_id ?? null;
  const [rows, setRows] = useState<HostTeamMember[]>([]);
  const [hostEvents, setHostEvents] = useState<EventItem[]>([]);
  const [search, setSearch] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [inviteOpen, setInviteOpen] = useState(false);

  async function load(include = includeArchived) {
    setRows(await fetchHostTeamMembers(include, hostId));
  }

  useEffect(() => {
    if (!hostId) return;
    let alive = true;
    void (async () => {
      try {
        const items = await fetchHostTeamMembers(includeArchived, hostId);
        if (alive) setRows(items);
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load members",
          );
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [hostId, includeArchived]);

  useEffect(() => {
    if (!hostId) return;
    void fetchMyEvents()
      .then(setHostEvents)
      .catch(() => setHostEvents([]));
  }, [hostId]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      [
        row.invited_email,
        row.invited_username,
        row.display_name,
        row.role,
        row.role_label,
        row.status,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q),
    );
  }, [rows, search]);

  async function run(
    id: string,
    action: () => Promise<unknown>,
    ok: string,
    fail: string,
  ) {
    setBusyId(id);
    setError(null);
    try {
      await action();
      toast.push({ title: ok, tone: "success" });
      await load();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : fail;
      setError(detail);
      toast.push({ title: fail, description: detail, tone: "danger" });
    } finally {
      setBusyId(null);
    }
  }

  function renderActions(row: HostTeamMember) {
    const busy = busyId === row.id;
    const archived = row.archived_at != null;
    return (
      <div className="flex flex-wrap justify-end gap-1.5 md:justify-start">
        <Link href={`/host/team/${row.id}`}>
          <Button size="sm" variant="secondary">
            Edit
          </Button>
        </Link>
        {row.status === "active" && !archived ? (
          <ConfirmAction
            label="Suspend"
            title="Suspend team member?"
            description={`Suspend ${memberLabel(row)}. Desk access stops until restored.`}
            confirmLabel="Suspend"
            disabled={busy}
            busy={busy}
            onConfirm={() =>
              run(
                row.id,
                () => suspendHostTeamMember(row.id, hostId),
                "Member suspended",
                "Suspend failed",
              )
            }
          />
        ) : null}
        {archived ? (
          <ConfirmAction
            label="Restore"
            title="Restore team member?"
            description={`Restore access for ${memberLabel(row)}.`}
            confirmLabel="Restore"
            disabled={busy}
            busy={busy}
            onConfirm={() =>
              run(
                row.id,
                () => restoreHostTeamMember(row.id, hostId),
                "Member restored",
                "Restore failed",
              )
            }
          />
        ) : (
          <ConfirmAction
            label="Remove"
            title="Remove team member?"
            description={`Remove ${memberLabel(row)} from your Pàdéyá host team.`}
            confirmLabel="Remove member"
            tone="danger"
            disabled={busy}
            busy={busy}
            onConfirm={() =>
              run(
                row.id,
                () => archiveHostTeamMember(row.id, hostId),
                "Member removed",
                "Remove failed",
              )
            }
          />
        )}
      </div>
    );
  }

  return (
    <RequireHostTeamManage>
      <DashboardShell
        tone="soft"
        eyebrow="Host Team"
        title="Team members"
        description="Accepted members — edit role, permissions, scope, or suspend/remove."
        actions={
          <Button type="button" onClick={() => setInviteOpen(true)}>
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

        {!loading && rows.length > 0 ? (
          <FilterBar
            trailing={
              <label className="flex cursor-pointer items-center gap-2 text-sm text-foreground">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-[var(--brand-green)]"
                  checked={includeArchived}
                  onChange={(e) => setIncludeArchived(e.target.checked)}
                />
                <span className="font-semibold">Show removed</span>
              </label>
            }
          >
            <Input
              label="Search"
              placeholder="Email, name, role, status…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </FilterBar>
        ) : null}

        {loading ? null : rows.length === 0 ? (
          <EmptyState
            title="No team members yet"
            description="Invite a collaborator to help with ticket and merch desk ops."
          />
        ) : (
          <DataTable
            rows={filtered}
            rowKey={(row) => row.id}
            emptyTitle="No matching members"
            emptyDescription="Try a different search term."
            columns={[
              {
                key: "member",
                header: "Member",
                primary: true,
                cell: (row) => (
                  <div className="flex items-start gap-3">
                    {row.avatar_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={row.avatar_url}
                        alt=""
                        className="mt-0.5 h-9 w-9 rounded-full object-cover"
                      />
                    ) : null}
                    <div className="min-w-0 space-y-0.5">
                      <p className="font-semibold text-foreground">
                        {memberLabel(row)}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {inviteePrimaryLabel(row)} · {row.role} ·{" "}
                        {scopeLabel(row.scope)}
                      </p>
                    </div>
                  </div>
                ),
              },
              {
                key: "status",
                header: "Status",
                cell: (row) => (
                  <div className="flex flex-wrap gap-1.5">
                    <StatusBadge status={row.status} />
                    {row.archived_at ? (
                      <StatusBadge status="archived" />
                    ) : null}
                  </div>
                ),
              },
              {
                key: "desk",
                header: "Desk access",
                cell: (row) => (
                  <span className="text-sm text-muted-foreground">
                    {deskAccessSummary(row.permissions)}
                  </span>
                ),
              },
              {
                key: "joined",
                header: "Joined",
                cell: (row) => (
                  <span className="text-sm text-muted-foreground">
                    {formatDateTime(row.accepted_at || row.created_at)}
                  </span>
                ),
              },
              {
                key: "actions",
                header: "Actions",
                cell: (row) => renderActions(row),
              },
            ]}
            mobileCard={(row) => (
              <Card className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-bold text-foreground">
                    {memberLabel(row)}
                  </h3>
                  <StatusBadge status={row.status} />
                </div>
                <p className="text-sm text-muted-foreground">
                  {row.role} · {deskAccessSummary(row.permissions)}
                </p>
                {renderActions(row)}
              </Card>
            )}
          />
        )}

        <TeamInviteModal
          open={inviteOpen}
          onClose={() => setInviteOpen(false)}
          hostId={hostId}
          isOwner={isOwner}
          events={hostEvents}
          onInvited={() => load()}
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
