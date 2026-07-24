"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import { Alert, Button, Card } from "@/components/ui";
import {
  generateAdminAI,
  recordAdminAIGenerationFeedback,
} from "@/lib/ai-api";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { AISuggestion } from "@/lib/types/ai";

const UNAVAILABLE =
  "AI is unavailable right now. You can keep reviewing source data.";

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const detail = err.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return UNAVAILABLE;
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    /* ignore */
  }
}

function parseChecklist(suggestion: string): string[] {
  return suggestion
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => /^[-*•]?\s*\[[ xX]?\]|^[-*•]\s+/.test(line) || line.startsWith("- ["));
}

export function AdminAISummaryPanel({
  feature,
  title,
  generateLabel = "Generate summary",
  description,
  links,
  className,
}: {
  feature: string;
  title: string;
  generateLabel?: string;
  description?: string;
  links?: { href: string; label: string }[];
  className?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AISuggestion | null>(null);

  const run = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const data = await generateAdminAI({ feature });
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }, [feature]);

  const feedback = useCallback(
    async (action: "applied" | "dismissed") => {
      if (!result?.usage_log_id) return;
      try {
        await recordAdminAIGenerationFeedback({
          usage_log_id: result.usage_log_id,
          action,
          applied_field: action === "applied" ? "admin_note_copy" : undefined,
        });
      } catch {
        /* non-blocking */
      }
    },
    [result?.usage_log_id],
  );

  const checklist = result ? parseChecklist(result.suggestion) : [];

  return (
    <Card className={cn("space-y-3", className)}>
      <div className="space-y-1">
        <p className="text-sm font-semibold text-foreground">{title}</p>
        <p className="text-xs text-muted-foreground">
          {description ||
            "AI summary is advisory. Review source data before taking action."}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button size="sm" disabled={busy} onClick={() => void run()}>
          {busy
            ? "Generating…"
            : result
              ? "Regenerate"
              : generateLabel}
        </Button>
        {result ? (
          <>
            <Button
              size="sm"
              variant="secondary"
              onClick={() =>
                void (async () => {
                  await copyText(result.suggestion);
                  await feedback("applied");
                })()
              }
            >
              Copy
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() =>
                void (async () => {
                  await feedback("dismissed");
                  setResult(null);
                  setError(null);
                })()
              }
            >
              Dismiss
            </Button>
          </>
        ) : null}
      </div>

      {error ? (
        <Alert tone="danger" title="AI summary">
          {error}
        </Alert>
      ) : null}

      {result ? (
        <div className="space-y-3 rounded-[var(--radius-md)] border border-border bg-surface-inset px-4 py-3">
          <pre className="whitespace-pre-wrap font-sans text-sm text-foreground">
            {result.suggestion}
          </pre>
          {checklist.length > 0 ? (
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Suggested actions (not executed)
              </p>
              <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                {checklist.map((item) => (
                  <li key={item}>{item.replace(/^[-*•]\s*(\[[ xX]?\])?\s*/, "")}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {links?.length ? (
            <div className="flex flex-wrap gap-2 pt-1">
              {links.map((link) => (
                <Link key={link.href} href={link.href}>
                  <Button size="sm" variant="secondary">
                    {link.label}
                  </Button>
                </Link>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}
