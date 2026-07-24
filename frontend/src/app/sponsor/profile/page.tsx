"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import {
  Alert,
  Button,
  Container,
  Input,
  SectionHeader,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchMySponsorProfile,
  updateMySponsorProfile,
  type SponsorProfile,
} from "@/lib/sponsor-profiles-api";

export default function SponsorProfilePage() {
  const { active } = useSponsorWorkspace();
  const [profile, setProfile] = useState<SponsorProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!active) return;
    void (async () => {
      try {
        setProfile(await fetchMySponsorProfile(active.sponsor_id));
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load profile");
      }
    })();
  }, [active]);

  if (!active) return null;

  async function save() {
    if (!profile || !active) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await updateMySponsorProfile(
        {
          short_bio: profile.short_bio,
          description: profile.description,
          website_url: profile.website_url,
          industry: profile.industry,
        },
        active.sponsor_id,
      );
      setProfile(updated);
      setNote("Profile saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitReview() {
    if (!active) return;
    setBusy(true);
    try {
      const updated = await updateMySponsorProfile(
        { submit_for_review: true },
        active.sponsor_id,
      );
      setProfile(updated);
      setNote("Submitted for review.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Submit failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Container className="space-y-6 py-6">
      <SectionHeader
        eyebrow="Manage"
        title="Sponsor profile"
        description="Public fields only appear after verification. Budget and campaign goals stay private on your public page."
        action={
          profile?.slug ? (
            <Link href={`/sponsors/${profile.slug}`}>
              <Button variant="secondary">Preview public page</Button>
            </Link>
          ) : null
        }
      />
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Saved">
          {note}
        </Alert>
      ) : null}
      {profile ? (
        <div className="space-y-4 max-w-lg">
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Short bio</span>
            <Textarea
              value={profile.short_bio ?? ""}
              onChange={(e) =>
                setProfile({ ...profile, short_bio: e.target.value })
              }
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Description</span>
            <Textarea
              value={profile.description ?? ""}
              onChange={(e) =>
                setProfile({ ...profile, description: e.target.value })
              }
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Website</span>
            <Input
              value={profile.website_url ?? ""}
              onChange={(e) =>
                setProfile({ ...profile, website_url: e.target.value })
              }
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Industry</span>
            <Input
              value={profile.industry ?? ""}
              onChange={(e) =>
                setProfile({ ...profile, industry: e.target.value })
              }
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button disabled={busy} onClick={() => void save()}>
              Save
            </Button>
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => void submitReview()}
            >
              Submit for review
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Loading…</p>
      )}
    </Container>
  );
}
