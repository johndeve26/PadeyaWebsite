"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PublicSponsorProfileView } from "@/components/sponsors/PublicSponsorProfileView";
import { Alert, Container, SkeletonCard } from "@/components/ui";
import {
  fetchPublicSponsorProfile,
  type SponsorPublicProfile,
} from "@/lib/sponsor-profiles-api";

export default function PublicSponsorProfilePage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const [profile, setProfile] = useState<SponsorPublicProfile | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    if (!slug) return;
    void (async () => {
      try {
        setProfile(await fetchPublicSponsorProfile(slug));
      } catch {
        setMissing(true);
      }
    })();
  }, [slug]);

  if (missing) {
    return (
      <Container className="py-16">
        <Alert tone="danger" title="Sponsor not found">
          This sponsor profile is private, unverified, or unavailable.
        </Alert>
      </Container>
    );
  }

  if (!profile) {
    return (
      <Container className="py-16">
        <SkeletonCard />
      </Container>
    );
  }

  return <PublicSponsorProfileView profile={profile} />;
}
