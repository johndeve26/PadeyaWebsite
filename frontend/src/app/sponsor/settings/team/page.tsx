"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import { SponsorTeamInviteModal } from "@/components/sponsor/team/SponsorTeamInviteModal";
import {
  Alert,
  Button,
  ConfirmAction,
  Container,
  DataTable,
  EmptyState,
  SectionHeader,
  Select,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  cancelSponsorTeamInvite,
  fetchSponsorTeam,
  removeSponsorTeamMember,
  resendSponsorTeamInvite,
  updateSponsorTeamMemberRole,
  type SponsorTeamInvite,
  type SponsorTeamMember,
} from "@/lib/sponsor-team-api";

const ROLE_OPTIONS = [
  { value: "admin", label: "Admin" },
  { value: "campaign_manager", label: "Campaign manager" },
  { value: "viewer", label: "Viewer" },
];

function canManageTeam(active: { is_owner: boolean; role: string } | null): boolean {
  if (!active) return false;
  return active.is_owner || active.role === "admin";
}

export default function SponsorTeamSettingsPage() {
  const toast = useToast();
  const { active } = useSponsorWorkspace();
  const sponsorId = active?.sponsor_id ?? null;
  const manage = canManageTeam(
    active
      ? { is_owner: active.is_owner, role: active.role }
      : null,
  );

  const [members, setMembers] = useState<SponsorTeamMember[]>([]);
  const [invites, setInvites] = useState<SponsorTeamInvite[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [roleDraft, setRoleDraft] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    if (!sponsorId) return;
    const data = await fetchSponsorTeam(sponsorId);
    setMembers(data.members);
    setInvites(data.invites);
  }, [sponsorId]);

  useEffect(() => {
    if (!sponsorId) return;
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load team");
      } finally {
        setLoading(false);
      }
    })();
  }, [load, sponsorId]);

  const removableMembers = useMemo(
    () => members.filter((m) => !m.is_owner && m.id),
    [members],
  );

  if (!sponsorId) return null;

  async function run(action: () => Promise<void>, ok: string) {
    try {
      await action();
      toast.success(ok);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Action failed");
    }
  }

  return (
    <Container className="space-y-8 py-6">
      <SectionHeader
        eyebrow="Settings"
        title="Team"
        description="Invite colleagues to your sponsor workspace. Only owner and admin can manage members."
        action={
          manage ? (
            <Button onClick={() => setInviteOpen(true)}>Invite member</Button>
          ) : null
        }
      />
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Members
        </h2>
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : members.length === 0 ? (
          <EmptyState title="No members" />
        ) : (
          <DataTable
            columns={[
              {
                key: "name",
                header: "Member",
                primary: true,
                cell: (r) => r.display_name || r.email || "—",
              },
              { key: "email", header: "Email", cell: (r) => r.email ?? "—" },
              {
                key: "role",
                header: "Role",
                cell: (r) =>
                  r.is_owner ? (
                    "Owner"
                  ) : manage && r.id ? (
                    <Select
                      className="h-8 text-xs"
                      value={roleDraft[r.id] ?? r.role}
                      onChange={(e) => {
                        const next = e.target.value;
                        setRoleDraft((d) => ({ ...d, [r.id!]: next }));
                      }}
                    >
                      {ROLE_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </Select>
                  ) : (
                    r.role.replace("_", " ")
                  ),
              },
              {
                key: "actions",
                header: "",
                cell: (r) =>
                  manage && r.id && !r.is_owner ? (
                    <div className="flex flex-wrap gap-2">
                      {roleDraft[r.id] && roleDraft[r.id] !== r.role ? (
                        <ConfirmAction
                          label="Save role"
                          title="Change role?"
                          description={`Update ${r.display_name || r.email} to ${roleDraft[r.id]}.`}
                          onConfirm={() =>
                            void run(async () => {
                              setBusyId(r.id!);
                              await updateSponsorTeamMemberRole(
                                sponsorId!,
                                r.id!,
                                roleDraft[r.id!]!,
                              );
                              setRoleDraft((d) => {
                                const copy = { ...d };
                                delete copy[r.id!];
                                return copy;
                              });
                              setBusyId(null);
                            }, "Role updated")
                          }
                        />
                      ) : null}
                      <ConfirmAction
                        label="Remove"
                        tone="danger"
                        title="Remove member?"
                        description="They will lose access to this sponsor workspace."
                        onConfirm={() =>
                          void run(async () => {
                            setBusyId(r.id!);
                            await removeSponsorTeamMember(sponsorId!, r.id!);
                            setBusyId(null);
                          }, "Member removed")
                        }
                      />
                    </div>
                  ) : null,
              },
            ]}
            rows={members}
            rowKey={(r) => r.id ?? `owner-${r.user_id}`}
            emptyTitle="No members"
          />
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Pending invites
        </h2>
        {invites.length === 0 ? (
          <EmptyState title="No pending invites" />
        ) : (
          <DataTable
            columns={[
              {
                key: "email",
                header: "Email",
                primary: true,
                cell: (r) => r.email,
              },
              { key: "role", header: "Role", cell: (r) => r.role },
              {
                key: "expires",
                header: "Expires",
                cell: (r) =>
                  r.invite_expires_at
                    ? formatDateTime(r.invite_expires_at)
                    : "—",
              },
              {
                key: "actions",
                header: "",
                cell: (r) =>
                  manage ? (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busyId === r.id}
                        onClick={() =>
                          void run(async () => {
                            setBusyId(r.id);
                            await resendSponsorTeamInvite(sponsorId!, r.id);
                            setBusyId(null);
                          }, "Invite resent")
                        }
                      >
                        Resend
                      </Button>
                      <ConfirmAction
                        label="Cancel"
                        tone="danger"
                        title="Cancel invite?"
                        description="The invite link will stop working."
                        onConfirm={() =>
                          void run(async () => {
                            setBusyId(r.id);
                            await cancelSponsorTeamInvite(sponsorId!, r.id);
                            setBusyId(null);
                          }, "Invite cancelled")
                        }
                      />
                    </div>
                  ) : null,
              },
            ]}
            rows={invites}
            rowKey={(r) => r.id}
          />
        )}
      </section>

      <SponsorTeamInviteModal
        open={inviteOpen}
        sponsorId={sponsorId}
        onClose={() => setInviteOpen(false)}
        onInvited={load}
        onError={setError}
        onSuccess={(msg) => toast.success(msg)}
      />
    </Container>
  );
}
