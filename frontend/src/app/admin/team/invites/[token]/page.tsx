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
import {
  acceptAdminTeamInvite,
  previewAdminTeamInvite,
  type AdminTeamInvitePreview,
} from "@/lib/admin-team/api";
import { formatDateTime } from "@/lib/format";

const WRONG_ACCOUNT_MSG =
  "Sign in with the invited email address to accept this admin team invite";

export default function AdminTeamInviteAcceptPage() {
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const { user, loading: authLoading, refreshUser } = useAuth();
  const token = typeof params.token === "string" ? params.token : "";
  const returnPath = `/admin/team/invites/${token}`;

  const [preview, setPreview] = useState<AdminTeamInvitePreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError("Invite not found");
      setLoading(false);
      return;
    }
    let cancelled = false;
    queueMicrotask(() => {
      void (async () => {
        try {
          const data = await previewAdminTeamInvite(token);
          if (!cancelled) {
            setPreview(data);
            setError(null);
          }
        } catch (err) {
          if (!cancelled) {
            setPreview(null);
            setError(
              err instanceof ApiError ? err.message : "Invite not found",
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
  }, [token]);

  const pending = preview?.status === "pending" && !preview.already_accepted;
  const wrongAccount =
    Boolean(error && /invited email/i.test(error)) ||
    Boolean(error && error.includes(WRONG_ACCOUNT_MSG));

  const linkExpired =
    (!loading && preview?.status === "expired" && !preview.already_accepted) ||
    (!loading &&
      !preview &&
      Boolean(
        error && /expir|not found|invalid|revoked|unavailable/i.test(error),
      ) &&
      !wrongAccount);

  async function onAccept() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await acceptAdminTeamInvite(token);
      await refreshUser();
      toast.push({
        title: "Invite accepted",
        description: "Welcome to the Pàdéyá admin team.",
        tone: "success",
      });
      router.replace("/admin");
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Could not accept invite";
      setError(message);
      toast.push({ title: "Accept failed", description: message, tone: "danger" });
    } finally {
      setBusy(false);
    }
  }

  if (linkExpired && !wrongAccount) {
    return (
      <ExpiredLinkState
        title="This invite link has expired"
        description="This admin team invite is no longer valid. Ask a platform administrator to send a new invite."
        primaryHref="/support"
        primaryLabel="Contact support"
      />
    );
  }

  return (
    <main className="mx-auto flex min-h-[70vh] max-w-lg flex-col justify-center px-4 py-12">
      <Card className="space-y-5 p-6">
        <SectionHeader
          title="Admin team invite"
          description="Join the Pàdéyá platform admin team."
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
                  Role
                </dt>
                <dd className="font-semibold text-foreground">
                  {preview.role_label || preview.role_name || "Admin"}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                  Invited email
                </dt>
                <dd className="text-muted-foreground">{preview.email_hint}</dd>
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
                  Sign in or create a Pàdéyá account with the invited email to
                  accept this invite.
                </Alert>
                <div className="flex flex-wrap gap-2">
                  <Link href={`/login?next=${encodeURIComponent(returnPath)}`}>
                    <Button>Sign in to accept</Button>
                  </Link>
                  <Link
                    href={`/register?next=${encodeURIComponent(returnPath)}`}
                  >
                    <Button variant="secondary">Create Pàdéyá account</Button>
                  </Link>
                </div>
              </div>
            ) : null}

            {user && pending && !wrongAccount ? (
              <Button disabled={busy} onClick={() => void onAccept()}>
                {busy ? "Working…" : "Accept invite"}
              </Button>
            ) : null}

            {preview.already_accepted || preview.status === "accepted" ? (
              <div className="space-y-3">
                <Alert tone="success">This invite was already accepted.</Alert>
                <Link href="/admin">
                  <Button>Open admin</Button>
                </Link>
              </div>
            ) : null}
          </div>
        ) : null}
      </Card>
    </main>
  );
}
