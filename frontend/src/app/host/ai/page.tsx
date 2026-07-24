"use client";

import Link from "next/link";
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
import {
  fetchAIStatus,
  fetchHostAIFeatures,
  generateHostAI,
} from "@/lib/ai-api";
import type { AIFeature, AIStatus, AISuggestion } from "@/lib/types/ai";

export default function HostAIPage() {
  const [features, setFeatures] = useState<AIFeature[]>([]);
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [feature, setFeature] = useState("");
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<AISuggestion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void Promise.all([fetchHostAIFeatures(), fetchAIStatus()])
      .then(([f, s]) => {
        setFeatures(f);
        setStatus(s);
        if (f[0]) setFeature(f[0].key);
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load AI"),
      )
      .finally(() => setLoading(false));
  }, []);

  async function onGenerate() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const suggestion = await generateHostAI({
        feature,
        notes: notes.trim() || undefined,
      });
      setResult(suggestion);
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
        eyebrow="AI Copilot"
        title="Host AI"
        description="Optional drafts for titles, captions, pricing ideas, and recaps on Pàdéyá. Nothing publishes or sends automatically — you confirm everything."
      >
        <PageToolbar>
          <Link href="/host">
            <Button size="sm" variant="ghost">
              Host home
            </Button>
          </Link>
          <Link href="/host/events">
            <Button size="sm" variant="secondary">
              Pick an event
            </Button>
          </Link>
        </PageToolbar>

        {loading ? <SkeletonLoader lines={3} /> : null}

        {status ? (
          <p className="text-sm text-muted-foreground">
            Provider: {status.provider}
            {status.enabled ? "" : " (disabled — using safe fallback drafts)"} · model{" "}
            {status.model}
          </p>
        ) : null}

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
              label="Notes (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Vibe, audience, constraints…"
              className="min-h-[90px]"
            />
            <Button disabled={busy || !feature} onClick={() => void onGenerate()}>
              {busy ? "Generating…" : "Generate suggestion"}
            </Button>
            <p className="text-sm text-muted-foreground">
              Suggestions require human confirmation. AI cannot publish events, send
              announcements, or change financial records.
            </p>
          </Card>
        ) : null}

        {result ? (
          <Card className="max-w-3xl space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-bold">{result.label}</h3>
              {result.used_fallback ? (
                <Badge>Fallback draft</Badge>
              ) : (
                <Badge tone="accent">AI</Badge>
              )}
              <Badge tone="dark">Review required</Badge>
            </div>
            <pre className="whitespace-pre-wrap font-sans text-sm text-muted-foreground">
              {result.suggestion}
            </pre>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => void navigator.clipboard.writeText(result.suggestion)}
            >
              Copy draft
            </Button>
          </Card>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
