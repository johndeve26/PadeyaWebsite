"use client";

import { Alert, Button } from "@/components/ui";

import type { BlogFactClaim } from "./types";
import { StudioPanel } from "./BlogStudioShell";

export function BlogFactReviewPanel({
  claims,
  busy,
  onRun,
}: {
  claims: BlogFactClaim[];
  busy?: boolean;
  onRun: () => void;
}) {
  return (
    <StudioPanel
      title="Fact review"
      description="Claims needing verification. AI never fabricates verified sources."
      actions={
        <Button size="sm" variant="secondary" disabled={busy} onClick={onRun}>
          {busy ? "Checking…" : "Review claims"}
        </Button>
      }
    >
      {claims.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          No claims flagged yet. Run after drafting factual content.
        </p>
      ) : (
        <ul className="space-y-2">
          {claims.map((c, i) => (
            <li
              key={`${c.claim.slice(0, 24)}-${i}`}
              className="rounded-[var(--radius-sm)] border border-border px-2 py-1.5 text-xs"
            >
              <p className="font-medium text-foreground">{c.claim}</p>
              <p className="mt-1 text-muted-foreground">
                {c.section ? `Section: ${c.section} · ` : ""}
                {c.review_status || "Needs verification"}
                {c.source_required ? " · Source required" : ""}
                {c.confidence ? ` · Confidence: ${c.confidence}` : ""}
              </p>
              {(c.source_urls || []).length > 0 ? (
                <ul className="mt-1 list-disc pl-4 text-muted-foreground">
                  {(c.source_urls || []).map((u) => (
                    <li key={u}>
                      <a
                        href={u}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary underline-offset-2 hover:underline"
                      >
                        {u}
                      </a>
                    </li>
                  ))}
                </ul>
              ) : (
                <Alert tone="warning" title="Unverified" className="mt-2">
                  Marked for manual verification — do not treat as cited fact.
                </Alert>
              )}
            </li>
          ))}
        </ul>
      )}
    </StudioPanel>
  );
}
