"use client";

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
  inviteePrimaryLabel,
  memberLabel,
  scopeLabel,
} from "@/lib/host-team-helpers";
import {
  fetchHostTeamInvites,
  resendHostTeamInvite,
  revokeHostTeamInvite,
} from "@/lib/hosts-lifecycle-api";
import type { EventItem } from "@/lib/types/events";
import type { HostTeamMember } from "@/lib/types/lifecycle";

export default function HostTeamInvitesPage() {
  const toast = useToast();
  const { active, isOwner } = useHostWorkspace();
  const hostId = active?.host_id ?? null;
  const [rows, setRows] = useState<HostTeamMember[]>([]);
  const [hostEvents, setHostEvents] = useState<EventItem[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteRole, setInviteRole] = useState("scanner");

  async function load() {
    setRows(await fetchHostTeamInvites(false, hostId));
  }

  useEffect(() => {
    if (!hostId) return;
    let alive = true;
    void (async () => {
      try {
        const items = await fetchHostTeamInvites(false, hostId);
        if (alive) setRows(items);
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load invites",
          );
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [hostId]);

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

  function openInvite(role: string) {
    setInviteRole(role);
    setInviteOpen(true);
  }

  function renderActions(row: HostTeamMember) {
    const busy = busyId === row.id;
    return (
      <div className="flex flex-wrap justify-end gap-1.5 md:justify-start">
        <Button
          size="sm"
          variant="secondary"
          disabled={busy || row.status !== "pending"}
          onClick={() => {
            setBusyId(row.id);
            void resendHostTeamInvite(row.id, hostId)
              .then(async () => {
                toast.push({ title: "Invite resent", tone: "success" });
                await load();
              })
              .catch((err) => {
                const detail =
                  err instanceof ApiError ? err.detail : "Resend failed";
                setError(detail);
                toast.push({
                  title: "Resend failed",
                  description: detail,
                  tone: "danger",
                });
              })
              .finally(() => setBusyId(null));
          }}
        >
          Resend
        </Button>
        <ConfirmAction
          label="Revoke"
          title="Revoke invite?"
          description={`Revoke the pending invite for ${memberLabel(row)}. They will not be able to accept it.`}
          confirmLabel="Revoke invite"
          tone="danger"
          disabled={busy}
          busy={busy}
          onConfirm={async () => {
            setBusyId(row.id);
            try {
              await revokeHostTeamInvite(row.id, hostId);
              toast.push({ title: "Invite revoked", tone: "success" });
              await load();
            } catch (err) {
              const detail =
                err instanceof ApiError ? err.detail : "Revoke failed";
              setError(detail);
              toast.push({
                title: "Revoke failed",
                description: detail,
                tone: "danger",
              });
            } finally {
              setBusyId(null);
            }
          }}
        />
      </div>
    );
  }

  return (
    <RequireHostTeamManage>
      <DashboardShell
        tone="soft"
        eyebrow="Host Team"
        title="Pending invites"
        description="Open invites waiting to be accepted. Revoke or resend anytime."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant="secondary"
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
              Invite merch
            </Button>
            <Button type="button" onClick={() => openInvite("scanner")}>
              Invite team member
            </Button>
          </div>
        }
      >
        <HostTeamSubnav />

        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {!loading && rows.length > 0 ? (
          <FilterBar>
            <Input
              label="Search"
              placeholder="Username, email, role, status…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </FilterBar>
        ) : null}

        {loading ? null : rows.length === 0 ? (
          <EmptyState
            title="No pending invites"
            description="Send an invite to add scanner, merch, or other team roles."
          />
        ) : (
          <DataTable
            rows={filtered}
            rowKey={(row) => row.id}
            emptyTitle="No matching invites"
            emptyDescription="Try a different search term."
            columns={[
              {
                key: "email",
                header: "Invitee",
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
                        {inviteePrimaryLabel(row)}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {row.display_name &&
                        row.invite_method === "username" &&
                        row.invited_username
                          ? `${row.display_name} · `
                          : ""}
                        {row.role_label || row.role} · {scopeLabel(row.scope)}
                      </p>
                    </div>
                  </div>
                ),
              },
              {
                key: "status",
                header: "Status",
                cell: (row) => <StatusBadge status={row.status} />,
              },
              {
                key: "expires",
                header: "Expires",
                cell: (row) => (
                  <span className="text-sm text-muted-foreground">
                    {row.invite_expires_at
                      ? formatDateTime(row.invite_expires_at)
                      : "—"}
                  </span>
                ),
              },
              {
                key: "sent",
                header: "Sent",
                cell: (row) => (
                  <span className="text-sm text-muted-foreground">
                    {formatDateTime(row.invited_at || row.created_at)}
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
                    {inviteePrimaryLabel(row)}
                  </h3>
                  <StatusBadge status={row.status} />
                </div>
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
