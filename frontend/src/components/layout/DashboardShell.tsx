import { type ReactNode } from "react";

import { Container, PageHeader } from "@/components/ui";
import { cn } from "@/lib/cn";

export function DashboardShell({
  title,
  description,
  eyebrow,
  children,
  actions,
  compact = false,
  tone = "light",
  hideHeader = false,
  operationalHeader = false,
  /** Fill remaining viewport height (e.g. inbox) — drops extra vertical padding. */
  fillViewport = false,
}: {
  title?: string;
  description?: string;
  eyebrow?: string;
  children?: ReactNode;
  actions?: ReactNode;
  compact?: boolean;
  /** light = page canvas; soft = muted marketplace feel */
  tone?: "light" | "soft";
  /** When true, skip the shell PageHeader (child pages supply their own). */
  hideHeader?: boolean;
  /** Compact titles for private host workspace pages. */
  operationalHeader?: boolean;
  fillViewport?: boolean;
}) {
  return (
    <main
      className={cn(
        "min-w-0 overflow-x-clip",
        tone === "soft" ? "bg-surface" : "bg-background",
        fillViewport
          ? "flex min-h-0 flex-1 flex-col overflow-hidden py-0"
          : compact
            ? "py-6 sm:py-8"
            : "py-8 sm:py-12",
      )}
    >
      <Container
        width="full"
        className={cn(
          "min-w-0",
          fillViewport
            ? "flex min-h-0 flex-1 flex-col !space-y-0"
            : "space-y-6 sm:space-y-7",
        )}
      >
        {!hideHeader && title ? (
          <PageHeader
            eyebrow={eyebrow}
            title={title}
            description={description}
            actions={actions}
            size={operationalHeader ? "operational" : "default"}
          />
        ) : null}
        {/* Keep page body spacing uniform — avoid per-page mb-* on siblings */}
        <div
          className={cn(
            "min-w-0",
            fillViewport
              ? "flex min-h-0 flex-1 flex-col"
              : "space-y-5 sm:space-y-6",
          )}
        >
          {children}
        </div>
      </Container>
    </main>
  );
}
