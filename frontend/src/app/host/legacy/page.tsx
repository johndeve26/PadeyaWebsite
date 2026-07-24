"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { LegacyPreviewPanel } from "@/components/legacy/studio/LegacyPreviewPanel";
import { LegacyStudioShell } from "@/components/legacy/studio/LegacyStudioShell";
import { Alert, Button, Card, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMyLegacyPage } from "@/lib/legacy-api";
import type { LegacyPage } from "@/lib/types/legacy";

export default function HostLegacyPage() {
  const [page, setPage] = useState<LegacyPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchMyLegacyPage();
        if (active) setPage(data);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Unable to load Legacy Page");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <LegacyStudioShell
      title="Legacy Page"
      description="Your permanent public reputation and monetization hub on Pàdéyá."
      actions={
        page ? (
          <Link href={page.share_path}>
            <Button size="sm" variant="secondary">
              Open public page
            </Button>
          </Link>
        ) : null
      }
    >
      {error ? (
        <Alert tone="danger" title="Unable to load">
          {error}
        </Alert>
      ) : null}

      {page ? (
        <div className="grid gap-8 xl:grid-cols-[340px_minmax(0,1fr)]">
          <div className="space-y-4">
            <Card className="space-y-3">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
                Studio
              </p>
              <h2 className="text-xl font-extrabold text-foreground">
                Manage your Legacy
              </h2>
              <p className="text-sm leading-relaxed text-muted-foreground">
                Edit identity, arrange content blocks, feature nights and Vault drops, then
                preview exactly what fans see.
              </p>
              <div className="flex flex-col gap-2">
                <Link href="/host/legacy/edit">
                  <Button className="w-full">Edit profile</Button>
                </Link>
                <Link href="/host/legacy/content">
                  <Button className="w-full" variant="secondary">
                    Content blocks
                  </Button>
                </Link>
                <Link href="/host/legacy/preview">
                  <Button className="w-full" variant="ghost">
                    Full preview
                  </Button>
                </Link>
              </div>
            </Card>
            <Card className="space-y-2">
              <p className="text-sm font-bold text-foreground">
                {page.content_blocks?.filter((b) => b.is_visible).length ?? 0} visible blocks
              </p>
              <p className="text-sm text-muted-foreground">
                Tier: {page.legacy_status}
                {page.tagline ? ` · ${page.tagline}` : ""}
              </p>
            </Card>
          </div>
          <LegacyPreviewPanel page={page} compact />
        </div>
      ) : !error ? (
        <SkeletonLoader lines={8} />
      ) : null}
    </LegacyStudioShell>
  );
}
