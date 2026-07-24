"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { ExpiredLinkState } from "@/components/not-found/ExpiredLinkState";
import {
  Alert,
  Button,
  Card,
  SectionHeader,
  SkeletonLoader,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  acceptHostTeamInvite,
  declineHostTeamInvite,
  previewHostTeamInvite,
} from "@/lib/hosts-lifecycle-api";
import { fetchHostWorkspaces } from "@/lib/hosts-api";
import { hostHomePathForWorkspace } from "@/lib/host-access";
import { writeActiveHostId } from "@/lib/host-workspace";
import type { HostTeamInvitePreview, HostTeamMember } from "@/lib/types/lifecycle";
import type { HostWorkspace } from "@/lib/types/host-workspace";

const WRONG_ACCOUNT_MSG =
  "This invite was sent to another Pàdéyá account.";

function workspaceFromInviteMember(
  member: HostTeamMember,
  preview: HostTeamInvitePreview | null,
): HostWorkspace {
  return {
    host_id: member.host_id,
    display_name: preview?.host_display_name ?? "Host workspace",
    slug: "",
    kind: "team_member",
    role: member.role,
    role_label: member.role_label,
    permissions: member.permissions,
    scope: member.scope,
    scoped_event_ids: member.scoped_event_ids,
    membership_id: member.id,
    is_owner: false,
  };
}

export default function HostTeamInviteAcceptPage() {
  const params = useParams<{ token: string }>();
  const token = params.token;
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [preview, setPreview] = useState<HostTeamInvitePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await previewHostTeamInvite(token);
        if (active) setPreview(data);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Invite not found");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [token]);

  const returnPath = `/team/invite/${token}`;
  const pending =
    preview?.status === "pending" && !preview.already_accepted;
  const isUsernameInvite = preview?.invite_method === "username";
  const inviteeLabel = isUsernameInvite ? "Username" : "Invited email";

  async function onAccept() {
    setBusy(true);
    setError(null);
    try {
      const member = await acceptHostTeamInvite(token);
      writeActiveHostId(member.host_id);
      const workspaces = await fetchHostWorkspaces().catch(() => []);
      const match = workspaces.find((w) => w.host_id === member.host_id);
      toast.push({
        title: "Welcome to the team",
        description: "You’re on this Pàdéyá host team.",
        tone: "success",
      });
      router.push(
        match
          ? hostHomePathForWorkspace(match)
          : hostHomePathForWorkspace(workspaceFromInviteMember(member, preview)),
      );
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.detail : "Could not accept invite";
      setError(detail);
      toast.push({ title: "Accept failed", description: detail, tone: "danger" });
    } finally {
      setBusy(false);
    }
  }

  async function onDecline() {
    setBusy(true);
    setError(null);
    try {
      await declineHostTeamInvite(token);
      toast.push({ title: "Invite declined", tone: "success" });
      router.push("/dashboard");
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Could not decline invite";
      setError(detail);
      toast.push({ title: "Decline failed", description: detail, tone: "danger" });
    } finally {
      setBusy(false);
    }
  }

  const wrongAccount =
    Boolean(error) &&
    (error === WRONG_ACCOUNT_MSG ||
      (isUsernameInvite &&
        Boolean(error?.toLowerCase().includes("another"))));

  const linkExpired =
    (!loading && preview?.status === "expired" && !preview.already_accepted) ||
    (!loading &&
      !preview &&
      Boolean(
        error &&
          /expir|not found|invalid|revoked|unavailable/i.test(error),
      ) &&
      !wrongAccount);

  if (linkExpired && !wrongAccount) {
    return (
      <ExpiredLinkState
        title="This invite link has expired"
        description="This host team invite is no longer valid. Ask the host to send a new invite from their Pàdéyá team page."
        primaryHref="/support"
        primaryLabel="Contact support"
      />
    );
  }

  return (
    <main className="mx-auto flex min-h-[70vh] max-w-lg flex-col justify-center px-4 py-12">
      <Card className="space-y-5 p-6">
        <SectionHeader
          title="Host team invite"
          description="Join a host team on Pàdéyá to help with event desk operations."
        />

        {loading || authLoading ? <SkeletonLoader lines={4} /> : null}

        {error ? (
          <Alert
            tone="danger"
            title={wrongAccount ? "Wrong account" : "Invite unavailable"}
          >
            {error}
          </Alert>
        ) : null}

        {!loading && preview ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={preview.status} />
              {preview.already_accepted ? (
                <StatusBadge status="active" />
              ) : null}
            </div>
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                  Host
                </dt>
                <dd className="font-semibold text-foreground">
                  {preview.host_display_name}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                  Role
                </dt>
                <dd className="text-foreground">{preview.role_label || preview.role}</dd>
              </div>
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                  {inviteeLabel}
                </dt>
                <dd className="text-muted-foreground">{preview.invited_email_hint}</dd>
              </div>
              {preview.expires_at ? (
                <div>
                  <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                    Expires
                  </dt>
                  <dd className="text-muted-foreground">
                    {formatDateTime(preview.expires_at)}
                  </dd>
                </div>
              ) : null}
            </dl>

            {!user && pending ? (
              <div className="space-y-3">
                <Alert tone="info" title="Sign in required">
                  {isUsernameInvite
                    ? "Sign in with the invited Pàdéyá account to accept this invite."
                    : "Sign in or create a Pàdéyá account with the invited email to accept this invite."}
                </Alert>
                <div className="flex flex-wrap gap-2">
                  <Link href={`/login?next=${encodeURIComponent(returnPath)}`}>
                    <Button>Sign in to accept</Button>
                  </Link>
                  {!isUsernameInvite ? (
                    <Link href={`/register?next=${encodeURIComponent(returnPath)}`}>
                      <Button variant="secondary">Create Pàdéyá account</Button>
                    </Link>
                  ) : null}
                </div>
              </div>
            ) : null}

            {user && pending && !wrongAccount ? (
              <div className="flex flex-wrap gap-2">
                <Button disabled={busy} onClick={() => void onAccept()}>
                  {busy ? "Working…" : "Accept invite"}
                </Button>
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void onDecline()}
                >
                  Decline
                </Button>
              </div>
            ) : null}

            {user && wrongAccount ? (
              <div className="space-y-3">
                <Alert tone="warning" title="Wrong Pàdéyá account">
                  {WRONG_ACCOUNT_MSG} Sign out and sign in with the account that
                  received this invite.
                </Alert>
                <Link href={`/login?next=${encodeURIComponent(returnPath)}`}>
                  <Button variant="secondary">Switch account</Button>
                </Link>
              </div>
            ) : null}

            {preview.already_accepted ? (
              <Alert tone="success" title="Already accepted">
                This invite was already accepted and cannot be reused.{" "}
                {user ? (
                  <Link href="/host" className="underline">
                    Open host dashboard
                  </Link>
                ) : null}
              </Alert>
            ) : null}

            {preview.status === "expired" && !preview.already_accepted ? (
              <Alert tone="warning" title="Invite expired">
                This invite expired and cannot be accepted. Ask the host to send
                a new one from their Pàdéyá team page.
              </Alert>
            ) : null}

            {(preview.status === "revoked" || preview.status === "declined") &&
            !preview.already_accepted ? (
              <Alert tone="warning" title="Invite revoked">
                This invite was revoked and cannot be accepted. Ask the host to
                send a new invite if you still need access.
              </Alert>
            ) : null}
          </div>
        ) : null}
      </Card>
    </main>
  );
}
