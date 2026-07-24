"use client";

import { LegacyPublicPageRenderer } from "@/components/legacy/LegacyPublicPageRenderer";
import type { LegacyPage } from "@/lib/types/legacy";

export function LegacyPreviewPanel({
  page,
  compact = false,
}: {
  page: LegacyPage;
  compact?: boolean;
}) {
  return (
    <div
      className={[
        "overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card dark:bg-surface-elevated",
        compact ? "max-h-[70vh] overflow-y-auto" : "",
      ].join(" ")}
    >
      <div className="border-b border-border bg-muted px-4 py-2 text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
        Public preview · /@{page.username}
      </div>
      <LegacyPublicPageRenderer page={page} />
    </div>
  );
}
