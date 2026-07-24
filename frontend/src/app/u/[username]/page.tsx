"use client";

import { useParams, notFound } from "next/navigation";
import { useEffect, useState } from "react";

import { LegacyPublicPageRenderer } from "@/components/legacy/LegacyPublicPageRenderer";
import { Container, SkeletonLoader } from "@/components/ui";
import { fetchLegacyPage } from "@/lib/legacy-api";
import type { LegacyPage } from "@/lib/types/legacy";

/**
 * Public host Legacy Page. Missing / inactive / private hosts use the global
 * branded 404 (privacy by omission — no distinct “hidden host” page).
 */
export default function PublicLegacyUsernamePage() {
  const params = useParams<{ username: string }>();
  const username = decodeURIComponent(params.username);
  const [page, setPage] = useState<LegacyPage | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchLegacyPage(username);
        if (active) setPage(data);
      } catch {
        if (active) setMissing(true);
      }
    })();
    return () => {
      active = false;
    };
  }, [username]);

  if (missing) {
    notFound();
  }

  if (!page) {
    return (
      <main className="bg-background py-20">
        <Container width="narrow">
          <SkeletonLoader lines={6} />
        </Container>
      </main>
    );
  }

  return <LegacyPublicPageRenderer page={page} />;
}
