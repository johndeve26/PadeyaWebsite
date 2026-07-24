"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import { Alert, Button, Container, SectionHeader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchMySponsorProfile,
  type SponsorProfile,
} from "@/lib/sponsor-profiles-api";

export default function SponsorSettingsPage() {
  const { active } = useSponsorWorkspace();
  const [profile, setProfile] = useState<SponsorProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    void (async () => {
      try {
        setProfile(await fetchMySponsorProfile(active.sponsor_id));
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load settings");
      }
    })();
  }, [active]);

  return (
    <Container className="space-y-4 py-6">
      <SectionHeader
        eyebrow="Manage"
        title="Settings"
        action={
          <Link href="/sponsor/settings/team">
            <Button variant="secondary">Team</Button>
          </Link>
        }
      />
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {profile ? (
        <dl className="grid gap-2 text-sm max-w-md">
          <div>
            <dt className="text-muted-foreground">Verification</dt>
            <dd className="font-semibold">{profile.verification_status}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Account status</dt>
            <dd className="font-semibold">{profile.status}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Visibility</dt>
            <dd className="font-semibold">{profile.visibility}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Contact email</dt>
            <dd>{profile.contact_email}</dd>
          </div>
        </dl>
      ) : (
        <p className="text-sm text-muted-foreground">Loading…</p>
      )}
    </Container>
  );
}
