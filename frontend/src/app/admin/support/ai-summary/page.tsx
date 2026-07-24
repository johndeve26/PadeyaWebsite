"use client";

import Link from "next/link";
import { useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  PageToolbar,
  SkeletonLoader,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { generateAdminSupportSummary } from "@/lib/ai-api";
import type { AISuggestion } from "@/lib/types/ai";

function SuggestionResult({ result }: { result: AISuggestion }) {
  const paragraphs = result.suggestion
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

  return (
    <Card className="max-w-3xl space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-lg font-extrabold text-foreground">{result.label}</h3>
        <Badge tone="dark">Suggestion only</Badge>
        {result.used_fallback ? <Badge tone="warning">Fallback</Badge> : null}
        {result.requires_human_confirmation ? (
          <Badge tone="outline">Needs review</Badge>
        ) : null}
      </div>
      <div className="space-y-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
        {paragraphs.map((para) => (
          <p key={para.slice(0, 48)}>{para}</p>
        ))}
      </div>
      <div className="flex flex-wrap gap-2 border-t border-border pt-3">
        <Badge tone="neutral">{result.provider}</Badge>
        {result.model_name ? (
          <Badge tone="outline">{result.model_name}</Badge>
        ) : null}
      </div>
    </Card>
  );
}

export default function AdminSupportAISummaryPage() {
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<AISuggestion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onGenerate() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await generateAdminSupportSummary(notes.trim() || undefined));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Support"
      title="AI support summary"
      description="Draft themes from refunds under review on Pàdéyá. Does not approve or reject refunds."
      actions={
        <Link href="/support/refunds">
          <Button size="sm">Open refund queue</Button>
        </Link>
      }
    >
      <PageToolbar>
        <Link href="/admin/ai">
          <Button size="sm" variant="ghost">
            Admin AI
          </Button>
        </Link>
        <Link href="/admin/refunds">
          <Button size="sm" variant="secondary">
            Admin refunds
          </Button>
        </Link>
        <Link href="/support/refunds">
          <Button size="sm" variant="ghost">
            Support refunds
          </Button>
        </Link>
      </PageToolbar>

      <Alert tone="info" title="Support tool">
        Summaries are drafts for triage only. Every refund decision still requires a
        human in the queue.
      </Alert>

      {error ? (
        <Alert tone="danger" title="Generation failed">
          {error}
        </Alert>
      ) : null}

      <Card className="max-w-2xl space-y-4">
        <Textarea
          label="Operator notes"
          hint="Optional focus area — e.g. recurring complaint themes."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Optional focus area…"
          rows={4}
        />
        <Button disabled={busy} onClick={() => void onGenerate()}>
          {busy ? "Summarizing…" : "Summarize complaints"}
        </Button>
      </Card>

      {busy ? <SkeletonLoader lines={4} /> : null}

      {result ? (
        <SuggestionResult result={result} />
      ) : !busy && !error ? (
        <EmptyState
          title="No summary yet"
          description="Run a summary to see complaint themes from refunds under review."
        />
      ) : null}
    </DashboardShell>
  );
}
