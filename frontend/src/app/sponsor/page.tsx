"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import { Alert, Button, Container, SectionHeader } from "@/components/ui";
import { fetchSponsorSaved } from "@/lib/sponsor-saved-api";

export default function SponsorOverviewPage() {
  const { active } = useSponsorWorkspace();
  const [savedCount, setSavedCount] = useState<number | null>(null);

  useEffect(() => {
    if (!active?.sponsor_id) return;
    void fetchSponsorSaved(active.sponsor_id)
      .then((d) => setSavedCount(d.saved_count))
      .catch(() => setSavedCount(null));
  }, [active?.sponsor_id]);

  return (
    <Container className="space-y-6 py-6">
      <SectionHeader
        eyebrow="Sponsor workspace"
        title="Overview"
        description="Browse host opportunities, manage inquiries, and keep your public sponsor profile up to date. Messaging and blasts require host approval — nothing is auto-matched."
      />
      {savedCount !== null ? (
        <p className="text-sm text-muted-foreground">
          Saved items:{" "}
          <Link href="/sponsor/saved" className="font-semibold text-accent underline">
            {savedCount}
          </Link>
        </p>
      ) : null}
      {active?.verification_status !== "verified" ? (
        <Alert tone="info" title="Verification pending">
          Your sponsor profile is not publicly verified yet. Submit for review from
          profile settings; admins approve before public directory listing.
        </Alert>
      ) : null}
      <div className="flex flex-wrap gap-3">
        <Link href="/sponsor/opportunities">
          <Button>Browse opportunities</Button>
        </Link>
        <Link href="/sponsor/inquiries">
          <Button variant="secondary">View inquiries</Button>
        </Link>
        <Link href="/sponsor/saved">
          <Button variant="ghost">Saved list</Button>
        </Link>
        <Link href="/sponsor/profile">
          <Button variant="ghost">Edit profile</Button>
        </Link>
      </div>
    </Container>
  );
}
