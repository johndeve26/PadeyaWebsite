"use client";

import { Badge, Button } from "@/components/ui";

import type { AutosaveStatus, BlogSeoScore, BlogWorkflowStepId } from "./types";
import { StudioPanel } from "./BlogStudioShell";

function statusLabel(status: AutosaveStatus) {
  switch (status) {
    case "saving":
      return "Saving…";
    case "saved":
      return "Saved";
    case "failed":
      return "Save failed";
    case "conflict":
      return "Version conflict";
    default:
      return "Ready";
  }
}

export function BlogSettingsSummary({
  status,
  categoryName,
  authorName,
  tagCount,
  featured,
  autosaveStatus,
  lastSavedAt,
  seoScore,
  workflowStep,
}: {
  status: string;
  categoryName?: string;
  authorName?: string;
  tagCount: number;
  featured: boolean;
  autosaveStatus: AutosaveStatus;
  lastSavedAt?: string | null;
  seoScore?: BlogSeoScore | null;
  workflowStep: BlogWorkflowStepId;
}) {
  const scoreTone =
    seoScore?.score == null
      ? "neutral"
      : seoScore.score >= 80
        ? "success"
        : seoScore.score >= 50
          ? "warning"
          : "danger";

  return (
    <StudioPanel title="Blog settings" description="Snapshot of publish-ready fields.">
      <dl className="space-y-2 text-xs">
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">Status</dt>
          <dd>
            <Badge tone={status === "published" ? "success" : "neutral"}>
              {status}
            </Badge>
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">Workflow</dt>
          <dd className="font-semibold capitalize">{workflowStep.replace("_", " ")}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">Category</dt>
          <dd>{categoryName || "None"}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">Author</dt>
          <dd>{authorName || "None"}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">Tags</dt>
          <dd>{tagCount}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">Featured</dt>
          <dd>{featured ? "Yes" : "No"}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">Autosave</dt>
          <dd className="font-semibold">{statusLabel(autosaveStatus)}</dd>
        </div>
        {lastSavedAt ? (
          <div className="flex justify-between gap-2">
            <dt className="text-muted-foreground">Last saved</dt>
            <dd>{new Date(lastSavedAt).toLocaleTimeString()}</dd>
          </div>
        ) : null}
      </dl>
      <div className="mt-3 flex items-center justify-between gap-2 border-t border-border pt-3">
        <span className="text-xs text-muted-foreground">SEO score</span>
        <Badge tone={scoreTone as "neutral" | "success" | "warning" | "danger"}>
          {seoScore?.score != null ? `${seoScore.score}` : "—"}
        </Badge>
      </div>
      {seoScore?.summary ? (
        <p className="mt-1 text-[11px] text-muted-foreground">{seoScore.summary}</p>
      ) : (
        <p className="mt-1 text-[11px] text-muted-foreground">
          Run SEO score after drafting.
        </p>
      )}
    </StudioPanel>
  );
}

export function BlogSeoScoreStatus({
  seoScore,
  onRefresh,
  busy,
}: {
  seoScore: BlogSeoScore | null;
  onRefresh: () => void;
  busy?: boolean;
}) {
  const indicators = seoScore
    ? (Object.entries(seoScore).filter(
        ([k, v]) =>
          k !== "score" &&
          k !== "summary" &&
          v &&
          typeof v === "object" &&
          "status" in (v as object),
      ) as Array<[string, { status: string; message?: string }]>)
    : [];

  return (
    <StudioPanel
      title="SEO status"
      actions={
        <Button size="sm" variant="ghost" disabled={busy} onClick={onRefresh}>
          Refresh
        </Button>
      }
    >
      {indicators.length === 0 ? (
        <p className="text-xs text-muted-foreground">No score yet.</p>
      ) : (
        <ul className="space-y-1.5">
          {indicators.map(([key, ind]) => (
            <li key={key} className="flex items-start justify-between gap-2 text-xs">
              <span className="text-muted-foreground">
                {key.replace(/_/g, " ")}
              </span>
              <span
                className={
                  ind.status === "ok"
                    ? "font-semibold text-primary"
                    : ind.status === "warn"
                      ? "font-semibold text-amber-700 dark:text-amber-400"
                      : "font-semibold text-danger"
                }
              >
                {ind.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </StudioPanel>
  );
}
