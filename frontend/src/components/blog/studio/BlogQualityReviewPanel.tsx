"use client";

import { Alert, Button } from "@/components/ui";

import type { BlogQualityReview } from "./types";
import { StudioPanel } from "./BlogStudioShell";

export function BlogQualityReviewPanel({
  review,
  busy,
  onRun,
}: {
  review: BlogQualityReview | null;
  busy?: boolean;
  onRun: () => void;
}) {
  const findings = review?.findings || [];
  const changes = review?.suggested_changes || [];

  return (
    <StudioPanel
      title="Quality review"
      description="Findings only — AI will not auto-modify your draft."
      actions={
        <Button size="sm" variant="secondary" disabled={busy} onClick={onRun}>
          {busy ? "Reviewing…" : "Run review"}
        </Button>
      }
    >
      {review?.summary ? (
        <Alert tone="info" title="Summary">
          {review.summary}
        </Alert>
      ) : (
        <p className="text-xs text-muted-foreground">
          Run a review after drafting to surface clarity, SEO, and CTA issues.
        </p>
      )}
      {findings.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {findings.map((f, i) => (
            <li
              key={`${f.category || "f"}-${i}`}
              className="rounded-[var(--radius-sm)] border border-border px-2 py-1.5 text-xs"
            >
              <p className="font-semibold text-foreground">
                {f.category || "Finding"}
                {f.severity ? (
                  <span className="ml-2 text-muted-foreground">
                    ({f.severity})
                  </span>
                ) : null}
              </p>
              {f.message ? (
                <p className="text-muted-foreground">{f.message}</p>
              ) : null}
              {f.suggestion ? (
                <p className="mt-1 text-foreground">Suggestion: {f.suggestion}</p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      {changes.length > 0 ? (
        <div className="mt-3">
          <p className="text-xs font-semibold">Suggested changes</p>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
            {changes.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </StudioPanel>
  );
}
