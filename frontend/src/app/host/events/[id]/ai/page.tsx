"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  PageToolbar,
  Select,
  SkeletonLoader,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchHostAIFeatures, generateHostEventAI } from "@/lib/ai-api";
import { fetchEventById } from "@/lib/events-api";
import type { AIFeature, AISuggestion } from "@/lib/types/ai";
import type { EventItem } from "@/lib/types/events";

const EVENT_FEATURES = new Set([
  "host.event.title",
  "host.event.description",
  "generate_event_title",
  "generate_event_description",
]);

export default function HostEventAIPage() {
  const params = useParams<{ id: string }>();
  const [event, setEvent] = useState<EventItem | null>(null);
  const [features, setFeatures] = useState<AIFeature[]>([]);
  const [feature, setFeature] = useState("");
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<AISuggestion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void Promise.all([fetchEventById(params.id), fetchHostAIFeatures()])
      .then(([ev, feats]) => {
        setEvent(ev);
        const filtered = feats.filter((f) => EVENT_FEATURES.has(f.key));
        setFeatures(filtered);
        if (filtered[0]) setFeature(filtered[0].key);
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load"),
      )
      .finally(() => setLoading(false));
  }, [params.id]);

  async function onGenerate() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(
        await generateHostEventAI(params.id, {
          feature,
          notes: notes.trim() || undefined,
        }),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Event AI"
        title={event ? `${event.title} · Copilot` : "Event Copilot"}
        description="Draft titles, captions, pricing ideas, and recaps for this event. You review and apply — AI never publishes or sends."
      >
        <PageToolbar>
          <Link href={`/host/events/${params.id}`}>
            <Button size="sm" variant="ghost">
              Back to event
            </Button>
          </Link>
          <Link href="/host/ai">
            <Button size="sm" variant="secondary">
              All host AI
            </Button>
          </Link>
          {event?.status === "completed" ? (
            <Link href={`/host/events/${params.id}/memory/edit`}>
              <Button size="sm" variant="ghost">
                Memory editor
              </Button>
            </Link>
          ) : null}
        </PageToolbar>

        {loading ? <SkeletonLoader lines={3} /> : null}

        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {!loading ? (
          <Card className="max-w-2xl space-y-3">
            <Select
              label="Feature"
              value={feature}
              onChange={(e) => setFeature(e.target.value)}
            >
              {features.map((f) => (
                <option key={f.key} value={f.key}>
                  {f.label}
                </option>
              ))}
            </Select>
            <Textarea
              label="Notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="min-h-[90px]"
            />
            <Button disabled={busy || !feature} onClick={() => void onGenerate()}>
              {busy ? "Generating…" : "Generate suggestion"}
            </Button>
          </Card>
        ) : null}

        {result ? (
          <Card className="max-w-3xl space-y-3">
            <div className="flex flex-wrap gap-2">
              <h3 className="font-bold">{result.label}</h3>
              {result.used_fallback ? (
                <Badge>Fallback</Badge>
              ) : (
                <Badge tone="accent">AI</Badge>
              )}
            </div>
            <pre className="whitespace-pre-wrap font-sans text-sm text-muted-foreground">
              {result.suggestion}
            </pre>
            <p className="text-sm text-muted-foreground">
              Paste into the event editor, memory recap, or announcement form after you
              approve the wording.
            </p>
          </Card>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
