"use client";

import { Button } from "@/components/ui";

import type { BlogRevisionPublic } from "./types";
import { StudioPanel } from "./BlogStudioShell";

export function BlogVersionHistory({
  revisions,
  busy,
  onRefresh,
  onPreview,
  onRestore,
  onCheckpoint,
}: {
  revisions: BlogRevisionPublic[];
  busy?: boolean;
  onRefresh: () => void;
  onPreview: (revision: BlogRevisionPublic) => void;
  onRestore: (revision: BlogRevisionPublic) => void;
  onCheckpoint: () => void;
}) {
  return (
    <StudioPanel
      title="Version history"
      description="Restore creates a new revision of the current draft first when possible."
      actions={
        <div className="flex gap-1">
          <Button size="sm" variant="ghost" disabled={busy} onClick={onRefresh}>
            Refresh
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={onCheckpoint}
          >
            Checkpoint
          </Button>
        </div>
      }
    >
      {revisions.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          No revisions yet. Save or run AI actions after the post exists.
        </p>
      ) : (
        <ul className="space-y-2">
          {revisions.map((r) => (
            <li
              key={r.id}
              className="rounded-[var(--radius-sm)] border border-border px-2 py-1.5 text-xs"
            >
              <p className="font-semibold text-foreground">
                {r.summary || r.action_type || "Revision"}
              </p>
              <p className="text-muted-foreground">
                {r.created_at
                  ? new Date(r.created_at).toLocaleString()
                  : r.id}
                {r.source ? ` · ${r.source}` : ""}
              </p>
              <div className="mt-2 flex flex-wrap gap-1">
                <Button size="sm" variant="ghost" onClick={() => onPreview(r)}>
                  Preview
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy}
                  onClick={() => {
                    if (
                      window.confirm(
                        "Restore this revision? Current editor content will be replaced after confirmation.",
                      )
                    ) {
                      onRestore(r);
                    }
                  }}
                >
                  Restore
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </StudioPanel>
  );
}
