"use client";

import { useCallback, useState } from "react";

import { Alert, Button, Card } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  generateFanPassportAI,
  recordFanAIGenerationFeedback,
} from "@/lib/ai-api";
import type { AISuggestion } from "@/lib/types/ai";

const FEATURE = "fan.passport.bio";

const UNAVAILABLE =
  "AI is unavailable right now. You can keep editing manually.";

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const detail = err.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return UNAVAILABLE;
}

export type FanPassportBioAIProps = {
  bio: string;
  aiNotes: string;
  disabled?: boolean;
  onApply: (bio: string) => void;
};

export function FanPassportBioAIAssist({
  bio,
  aiNotes,
  disabled = false,
  onApply,
}: FanPassportBioAIProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AISuggestion | null>(null);

  const generate = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const suggestion = await generateFanPassportAI({
        feature: FEATURE,
        notes: aiNotes || undefined,
        extra: {
          bio: bio || "",
          existing_bio: bio || "",
          user_notes: aiNotes || "",
        },
      });
      setResult(suggestion);
    } catch (err) {
      setResult(null);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }, [aiNotes, bio]);

  function applyOption(text: string) {
    onApply(text);
    if (result?.usage_log_id) {
      void recordFanAIGenerationFeedback({
        usage_log_id: result.usage_log_id,
        action: "applied",
        applied_field: "passport_bio",
      }).catch(() => undefined);
    }
    setResult(null);
  }

  async function copyOptions() {
    if (!result) return;
    const text =
      result.options?.join("\n\n") || result.suggestion || "";
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      setError("Could not copy to clipboard.");
    }
  }

  const options = result?.options?.length
    ? result.options
    : result?.suggestion
      ? [result.suggestion]
      : [];

  return (
    <Card className="space-y-3 border-dashed bg-surface-muted/40">
      <div className="space-y-1">
        <h3 className="text-sm font-extrabold">Improve with AI</h3>
        <p className="text-xs text-muted-foreground">
          Draft-only — fills the bio field; you still save Passport settings
          manually. Visibility is unchanged.
        </p>
      </div>

      <Button
        type="button"
        size="sm"
        variant="secondary"
        disabled={busy || disabled}
        onClick={() => void generate()}
      >
        {busy ? "Generating…" : "Improve with AI"}
      </Button>

      {error ? (
        <Alert tone="danger" title="AI">
          {error}
        </Alert>
      ) : null}

      {result ? (
        <div className="space-y-3 rounded-lg border border-border bg-card p-3 text-sm">
          {result.disclaimer ? (
            <p className="text-xs text-muted-foreground">{result.disclaimer}</p>
          ) : null}
          <ul className="space-y-3">
            {options.map((opt, idx) => (
              <li
                key={idx}
                className="space-y-2 rounded-md border border-border/80 p-3"
              >
                <p className="whitespace-pre-wrap text-muted-foreground">{opt}</p>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => applyOption(opt)}
                >
                  Apply to bio
                </Button>
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => void copyOptions()}
            >
              Copy
            </Button>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={busy}
              onClick={() => void generate()}
            >
              Regenerate
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setResult(null)}
            >
              Dismiss
            </Button>
          </div>
        </div>
      ) : null}
    </Card>
  );
}
