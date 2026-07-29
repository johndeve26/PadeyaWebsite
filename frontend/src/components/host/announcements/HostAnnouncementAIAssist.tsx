"use client";

import { useCallback, useState } from "react";

import { Alert, Button, Card } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  generateHostAI,
  recordHostAIGenerationFeedback,
} from "@/lib/ai-api";
import type { AISuggestion } from "@/lib/types/ai";

const FEATURE = "host.announcements.draft";

const UNAVAILABLE =
  "AI is unavailable right now. You can keep editing manually.";

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const detail = err.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return UNAVAILABLE;
}

export type HostAnnouncementAIProps = {
  title: string;
  bodyEmail: string;
  bodyWhatsapp: string;
  channel: string;
  segmentKey: string;
  segmentLabel: string;
  eventId: string;
  hostNotes: string;
  personalizeWithName?: boolean;
  onApply: (patch: {
    title?: string;
    bodyEmail: string;
    bodyWhatsapp?: string;
  }) => void;
};

export function HostAnnouncementAIAssist({
  title,
  bodyEmail,
  bodyWhatsapp,
  channel,
  segmentKey,
  segmentLabel,
  eventId,
  hostNotes,
  personalizeWithName = false,
  onApply,
}: HostAnnouncementAIProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AISuggestion | null>(null);

  const generate = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const suggestion = await generateHostAI({
        feature: FEATURE,
        event_id: eventId || undefined,
        notes: hostNotes || undefined,
        extra: {
          channel,
          announcement_type: channel,
          audience_label: segmentLabel || segmentKey,
          host_notes: hostNotes || "",
          personalize_with_name: personalizeWithName ? "yes" : "no",
        },
      });
      setResult(suggestion);
    } catch (err) {
      setResult(null);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }, [
    channel,
    eventId,
    hostNotes,
    personalizeWithName,
    segmentKey,
    segmentLabel,
  ]);

  function applyDraft() {
    if (!result) return;
    const subject =
      result.announcement_subject?.trim() ||
      title ||
      "Announcement draft";
    const email =
      result.announcement_email_body?.trim() ||
      result.suggestion ||
      bodyEmail;
    const wa =
      result.announcement_whatsapp_body?.trim() || bodyWhatsapp;
    onApply({
      title: subject,
      bodyEmail: email,
      bodyWhatsapp: wa || undefined,
    });
    if (result.usage_log_id) {
      void recordHostAIGenerationFeedback({
        usage_log_id: result.usage_log_id,
        action: "applied",
        applied_field: "announcement_draft",
      }).catch(() => undefined);
    }
    setResult(null);
  }

  async function copyDraft() {
    if (!result) return;
    const text = [
      result.announcement_subject
        ? `Subject: ${result.announcement_subject}`
        : null,
      result.announcement_email_body || result.suggestion,
      result.announcement_whatsapp_body
        ? `WhatsApp: ${result.announcement_whatsapp_body}`
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
    <Card className="space-y-3 border-dashed bg-surface-muted/40">
      <div className="space-y-1">
        <h3 className="text-sm font-extrabold">Generate with AI</h3>
        <p className="text-xs text-muted-foreground">
          Draft-only — review subject and body before creating or dispatching.
          Send stays manual.
          {personalizeWithName
            ? " Personalization is on: drafts should use {{name}}."
            : null}
        </p>
      </div>

      <Button
        type="button"
        size="sm"
        variant="secondary"
        disabled={busy}
        onClick={() => void generate()}
      >
        {busy ? "Generating…" : "Generate with AI"}
      </Button>

      {error ? (
        <Alert tone="danger" title="AI">
          {error}
        </Alert>
      ) : null}

      {result ? (
        <div className="space-y-3 rounded-lg border border-border bg-card p-3 text-sm">
          {result.used_fallback ? (
            <Alert tone="warning" title="Template draft (not live AI)">
              {result.fallback_reason ||
                "The OpenAI/network provider did not run. Check Admin → Pàdéyá AI: global enable, API key on the server, and feature routing."}
            </Alert>
          ) : null}
          {result.disclaimer ? (
            <p className="text-xs text-muted-foreground">{result.disclaimer}</p>
          ) : null}
          <div className="rounded-md border border-border bg-surface-muted/40 px-3 py-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Email subject
            </p>
            <p className="mt-1 font-semibold text-foreground">
              {result.announcement_subject?.trim() ||
                "(No subject returned — edit the subject field after apply)"}
            </p>
          </div>
          <p className="whitespace-pre-wrap text-muted-foreground">
            {result.announcement_email_body || result.suggestion}
          </p>
          {result.announcement_whatsapp_body ? (
            <p className="text-xs">
              <span className="font-semibold">WhatsApp: </span>
              {result.announcement_whatsapp_body}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" onClick={applyDraft}>
              Apply subject + body
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => void copyDraft()}>
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
            <Button type="button" size="sm" variant="ghost" onClick={() => setResult(null)}>
              Dismiss
            </Button>
          </div>
        </div>
      ) : null}
    </Card>
  );
}
