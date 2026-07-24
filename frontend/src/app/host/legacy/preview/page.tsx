"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { LegacyPreviewPanel } from "@/components/legacy/studio/LegacyPreviewPanel";
import { LegacyStudioShell } from "@/components/legacy/studio/LegacyStudioShell";
import { Alert, Button, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMyLegacyPage } from "@/lib/legacy-api";
import type { LegacyPage } from "@/lib/types/legacy";

export default function HostLegacyPreviewPage() {
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
          setError(err instanceof ApiError ? err.detail : "Unable to load preview");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <LegacyStudioShell
      title="Legacy preview"
      description="Exact public layout using your current visible content blocks."
      actions={
        page ? (
          <div className="flex flex-wrap gap-2">
            <Link href="/host/legacy/content">
              <Button size="sm" variant="secondary">
                Edit blocks
              </Button>
            </Link>
            <Link href={page.share_path}>
              <Button size="sm">Open public page</Button>
            </Link>
          </div>
        ) : null
      }
    >
      {error ? (
        <Alert tone="danger" title="Unable to load">
          {error}
        </Alert>
      ) : null}
      {page ? <LegacyPreviewPanel page={page} /> : !error ? <SkeletonLoader lines={10} /> : null}
    </LegacyStudioShell>
  );
}
