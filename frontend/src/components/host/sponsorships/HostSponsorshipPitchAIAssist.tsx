"use client";

import { useCallback, useState } from "react";

import { Alert, Button, Card } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  generateHostAI,
  recordHostAIGenerationFeedback,
} from "@/lib/ai-api";
import type { AISuggestion } from "@/lib/types/ai";

const FEATURE = "host.sponsorship.pitch";

const UNAVAILABLE =
  "AI is unavailable right now. You can keep editing manually.";

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const detail = err.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return UNAVAILABLE;
}

export type HostSponsorshipPitchAIProps = {
  slotType: string;
  slotTypeLabel: string;
  hostNotes: string;
  onApply: (patch: {
    pitch: string;
    audienceNotes: string;
    slotTitle?: string;
    slotDescription?: string;
  }) => void;
  compact?: boolean;
};

function buildAudienceNotes(result: AISuggestion): string {
  const parts: string[] = [];
  if (result.sponsorship_value_bullets?.trim()) {
    parts.push(`Value proposition:\n${result.sponsorship_value_bullets.trim()}`);
  }
  if (result.sponsorship_audience_summary?.trim()) {
    parts.push(`Audience & events:\n${result.sponsorship_audience_summary.trim()}`);
  }
  if (result.sponsorship_package_wording?.trim()) {
    parts.push(`Package wording:\n${result.sponsorship_package_wording.trim()}`);
  }
  if (result.sponsorship_follow_up_message?.trim()) {
    parts.push(
      `Follow-up message (draft — send manually):\n${result.sponsorship_follow_up_message.trim()}`,
    );
  }
  return parts.join("\n\n");
}

export function HostSponsorshipPitchAIAssist({
  slotType,
  slotTypeLabel,
  hostNotes,
  onApply,
  compact = false,
}: HostSponsorshipPitchAIProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AISuggestion | null>(null);

  const generate = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const suggestion = await generateHostAI({
        feature: FEATURE,
        notes: hostNotes || undefined,
        extra: {
          slot_type: slotType,
          slot_type_label: slotTypeLabel,
          host_notes: hostNotes || "",
        },
      });
      setResult(suggestion);
    } catch (err) {
      setResult(null);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }, [hostNotes, slotType, slotTypeLabel]);

  function applyDraft() {
    if (!result) return;
    const pitch =
      result.sponsorship_short_pitch?.trim() ||
      result.suggestion ||
      "";
    const title = result.sponsorship_pitch_title?.trim();
    const pitchWithTitle =
      title && !pitch.startsWith(title)
        ? `${title}\n\n${pitch}`
        : pitch;
    onApply({
      pitch: pitchWithTitle,
      audienceNotes: buildAudienceNotes(result),
      slotTitle: title,
      slotDescription: result.sponsorship_package_wording?.trim() || undefined,
    });
    if (result.usage_log_id) {
      void recordHostAIGenerationFeedback({
        usage_log_id: result.usage_log_id,
        action: "applied",
        applied_field: "sponsorship_pitch",
      }).catch(() => undefined);
    }
    setResult(null);
  }

  async function copyDraft() {
    if (!result) return;
    const text = [
      result.sponsorship_pitch_title
        ? `Title: ${result.sponsorship_pitch_title}`
        : null,
      result.sponsorship_short_pitch || result.suggestion,
      result.sponsorship_value_bullets
        ? `Value:\n${result.sponsorship_value_bullets}`
        : null,
      result.sponsorship_audience_summary
        ? `Audience:\n${result.sponsorship_audience_summary}`
        : null,
      result.sponsorship_package_wording
        ? `Package:\n${result.sponsorship_package_wording}`
        : null,
      result.sponsorship_follow_up_message
        ? `Follow-up:\n${result.sponsorship_follow_up_message}`
        : null,
    ]
      .filter(Boolean)
      .join("\n\n");
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      setError("Could not copy to clipboard.");
    }
  }

  return (
    <Card
      className={
        compact
          ? "space-y-3 border-dashed bg-surface-muted/30 p-3"
          : "space-y-3 border-dashed bg-surface-muted/40"
      }
    >
      <div className="space-y-1">
        <h3 className="text-sm font-extrabold">
          Generate sponsorship pitch with AI
        </h3>
        <p className="text-xs text-muted-foreground">
          Draft-only — review before saving or messaging brands. Nothing is sent
          automatically.
        </p>
      </div>

      <Button
        type="button"
        size="sm"
        variant="secondary"
        disabled={busy}
        onClick={() => void generate()}
      >
        {busy ? "Generating…" : "Generate sponsorship pitch with AI"}
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
          {result.sponsorship_pitch_title ? (
            <p>
              <span className="font-semibold">Title: </span>
              {result.sponsorship_pitch_title}
            </p>
          ) : null}
          <p className="whitespace-pre-wrap text-muted-foreground">
            {result.sponsorship_short_pitch || result.suggestion}
          </p>
          {result.sponsorship_value_bullets ? (
            <p className="whitespace-pre-wrap text-xs">
              <span className="font-semibold">Value: </span>
              {result.sponsorship_value_bullets}
            </p>
          ) : null}
          {result.sponsorship_follow_up_message ? (
            <p className="text-xs text-muted-foreground">
              <span className="font-semibold">Follow-up: </span>
              {result.sponsorship_follow_up_message}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" onClick={applyDraft}>
              Apply to draft
            </Button>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => void copyDraft()}
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
