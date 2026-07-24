"use client";

import { useCallback, useState } from "react";

import { Alert, Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  generateHostAI,
  recordHostAIGenerationFeedback,
} from "@/lib/ai-api";
import type { AISuggestion } from "@/lib/types/ai";
import { cn } from "@/lib/cn";

import type { EventStudioValues } from "../types";

const FEATURE_TITLE = "host.event.title";
const FEATURE_DESCRIPTION = "host.event.description";

const UNAVAILABLE =
  "AI is unavailable right now. You can keep editing manually.";

function studioExtra(
  values: EventStudioValues,
  categoryName: string | null | undefined,
): Record<string, string> {
  return {
    title: values.title || "",
    notes: values.short_tagline || "",
    city: values.city || "",
    area: values.area || "",
    category: categoryName || "",
    vibe:
      values.vibe ||
      values.description?.slice(0, 240) ||
      values.short_tagline ||
      "",
    date: values.start_datetime || "",
    capacity: values.capacity || "",
    venue: values.venue_name || "",
    location_visibility: values.location_visibility || "full_public",
    short_tagline: values.short_tagline || "",
    ticket_tiers: values.ticket_drafts
      .map((t) => t.name)
      .filter(Boolean)
      .join(", "),
  };
}

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const detail = err.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return UNAVAILABLE;
}

export function StudioTitleAI({
  values,
  categoryName,
  eventId,
  onApplyTitle,
}: {
  values: EventStudioValues;
  categoryName?: string | null;
  eventId?: string | null;
  onApplyTitle: (title: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AISuggestion | null>(null);

  const generate = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const suggestion = await generateHostAI({
        feature: FEATURE_TITLE,
        event_id: eventId || undefined,
        notes: values.short_tagline || undefined,
        extra: studioExtra(values, categoryName),
      });
      setResult(suggestion);
    } catch (err) {
      setResult(null);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }, [categoryName, eventId, values]);

  async function applyOption(option: string) {
    onApplyTitle(option);
    if (result?.usage_log_id) {
      void recordHostAIGenerationFeedback({
        usage_log_id: result.usage_log_id,
        action: "applied",
        event_id: eventId || undefined,
        applied_field: "title",
        selected_option: option,
      }).catch(() => undefined);
    }
  }

  const options =
    result?.options && result.options.length > 0
      ? result.options
      : result?.suggestion
        ? result.suggestion
            .split("\n")
            .map((line) => line.replace(/^\d+[.)]\s*/, "").trim())
            .filter((line) => line.length >= 3)
        : [];

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => void generate()}
        >
          {busy ? "Generating…" : "Generate title ideas"}
        </Button>
        <span className="text-xs text-muted-foreground">Generate with AI</span>
      </div>
      <p className="text-xs text-muted-foreground">
        Draft only — review before publishing. AI suggestions can be edited
        before saving.
      </p>
      {error ? (
        <Alert tone="warning" title="AI unavailable">
          {error}
        </Alert>
      ) : null}
      {result && options.length > 0 ? (
        <div
          className={cn(
            "space-y-2 rounded-[var(--radius-md)] border border-border/80",
            "bg-muted/30 p-3",
          )}
        >
          <p className="text-xs font-semibold text-muted-foreground">
            Title ideas
            {result.used_fallback ? " · template draft" : ""}
          </p>
          <ul className="space-y-1.5">
            {options.map((opt) => (
              <li key={opt}>
                <button
                  type="button"
                  className={cn(
                    "w-full rounded-[var(--radius-sm)] border border-border/70",
                    "bg-card px-3 py-2 text-left text-sm text-foreground",
                    "hover:border-primary/40 hover:bg-surface-muted",
                  )}
                  onClick={() => void applyOption(opt)}
                >
                  {opt}
                </button>
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-2 pt-1">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={() => void generate()}
            >
              Regenerate
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                setResult(null);
                if (result.usage_log_id) {
                  void recordHostAIGenerationFeedback({
                    usage_log_id: result.usage_log_id,
                    action: "dismissed",
                    event_id: eventId || undefined,
                  }).catch(() => undefined);
                }
              }}
            >
              Dismiss
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function StudioDescriptionAI({
  values,
  categoryName,
  eventId,
  onApplyDescription,
}: {
  values: EventStudioValues;
  categoryName?: string | null;
  eventId?: string | null;
  onApplyDescription: (description: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AISuggestion | null>(null);

  const generate = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const suggestion = await generateHostAI({
        feature: FEATURE_DESCRIPTION,
        event_id: eventId || undefined,
        notes: values.short_tagline || undefined,
        extra: studioExtra(values, categoryName),
      });
      setResult(suggestion);
    } catch (err) {
      setResult(null);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }, [categoryName, eventId, values]);

  async function apply() {
    if (!result?.suggestion) return;
    onApplyDescription(result.suggestion);
    void recordHostAIGenerationFeedback({
      usage_log_id: result.usage_log_id,
      action: "applied",
      event_id: eventId || undefined,
      applied_field: "description",
    }).catch(() => undefined);
  }

  async function copyText() {
    if (!result?.suggestion || !navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(result.suggestion);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => void generate()}
        >
          {busy ? "Generating…" : "Generate description"}
        </Button>
        <span className="text-xs text-muted-foreground">Generate with AI</span>
      </div>
      <p className="text-xs text-muted-foreground">
        Draft only — review before publishing. AI suggestions can be edited
        before saving.
      </p>
      {error ? (
        <Alert tone="warning" title="AI unavailable">
          {error}
        </Alert>
      ) : null}
      {result?.suggestion ? (
        <div
          className={cn(
            "space-y-3 rounded-[var(--radius-md)] border border-border/80",
            "bg-muted/30 p-3",
          )}
        >
          <p className="text-xs font-semibold text-muted-foreground">
            Description draft
            {result.used_fallback ? " · template draft" : ""}
          </p>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
            {result.suggestion}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" onClick={() => void apply()}>
              Apply to description
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
              onClick={() => void copyText()}
            >
              Copy
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                setResult(null);
                void recordHostAIGenerationFeedback({
                  usage_log_id: result.usage_log_id,
                  action: "dismissed",
                  event_id: eventId || undefined,
                }).catch(() => undefined);
              }}
            >
              Dismiss
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
