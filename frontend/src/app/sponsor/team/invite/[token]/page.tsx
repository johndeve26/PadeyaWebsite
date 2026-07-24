"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { Alert, Button, Container } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  acceptSponsorTeamInvite,
  previewSponsorTeamInvite,
} from "@/lib/sponsor-team-api";

function AcceptInner() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const token = params.token;
  const [preview, setPreview] = useState<{
    sponsor_display_name: string;
    role: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) return;
    void (async () => {
      try {
        setPreview(await previewSponsorTeamInvite(token));
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Invalid invite");
      }
    })();
  }, [token]);

  async function accept() {
    if (!token) return;
    setBusy(true);
    try {
      await acceptSponsorTeamInvite(token);
      router.push("/sponsor");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not accept invite");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Container className="max-w-md space-y-4 py-16">
      <h1 className="text-xl font-bold">Sponsor team invite</h1>
      {error ? (
        <Alert tone="danger" title="Invite unavailable">
          {error}
        </Alert>
      ) : null}
      {preview ? (
        <>
          <p className="text-sm text-muted-foreground">
            Join <strong>{preview.sponsor_display_name}</strong> on Pàdéyá as{" "}
            <strong>{preview.role.replace("_", " ")}</strong>.
          </p>
          <Button disabled={busy} onClick={() => void accept()}>
            Accept invite
          </Button>
        </>
      ) : !error ? (
        <p className="text-sm text-muted-foreground">Loading invite…</p>
      ) : null}
      <Link href="/dashboard" className="text-sm text-accent underline">
        Back to dashboard
      </Link>
    </Container>
  );
}

export default function SponsorTeamInviteAcceptPage() {
  return (
    <RequireAuth>
      <AcceptInner />
    </RequireAuth>
  );
}
