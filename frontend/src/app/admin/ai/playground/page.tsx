"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  PageToolbar,
  Select,
  SkeletonLoader,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAIStatus,
  fetchAdminAIFeatures,
  generateAdminAI,
} from "@/lib/ai-api";
import type { AIFeature, AIStatus, AISuggestion } from "@/lib/types/ai";

function SuggestionResult({ result }: { result: AISuggestion }) {
  const paragraphs = result.suggestion
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

  return (
    <Card className="max-w-3xl space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-lg font-extrabold text-foreground">{result.label}</h3>
        {result.used_fallback ? (
          <Badge tone="warning">Fallback</Badge>
        ) : (
          <Badge tone="accent">AI</Badge>
        )}
        {result.requires_human_confirmation ? (
          <Badge tone="outline">Needs review</Badge>
        ) : null}
        {result.can_modify_finance ? null : (
          <Badge tone="dark">No finance writes</Badge>
        )}
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

export default function AdminAIPlaygroundPage() {
  const [features, setFeatures] = useState<AIFeature[]>([]);
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [feature, setFeature] = useState("");
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<AISuggestion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void Promise.all([fetchAdminAIFeatures(), fetchAIStatus()])
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
      setResult(
        await generateAdminAI({
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
    <DashboardShell
      tone="soft"
      eyebrow="Pàdéyá AI"
      title="AI playground"
      description="Operator draft playground. AI cannot approve refunds, mark payouts paid, or edit the ledger."
      actions={
        <Link href="/admin/ai">
          <Button size="sm" variant="secondary">
            AI controls
          </Button>
        </Link>
      }
    >
      <PageToolbar>
        <Link href="/admin/ai">
          <Button size="sm" variant="ghost">
            AI hub
          </Button>
        </Link>
        <Link href="/admin/ai/settings">
          <Button size="sm" variant="ghost">
            Settings
          </Button>
        </Link>
        <Link href="/admin/support/ai-summary">
          <Button size="sm" variant="ghost">
            Support AI summary
          </Button>
        </Link>
      </PageToolbar>

      {loading && !error ? <SkeletonLoader lines={3} /> : null}

      {status ? (
        <Alert
          tone={
            status.disabled_by_environment
              ? "danger"
              : status.enabled
                ? "info"
                : "warning"
          }
          title={
            status.status_label ||
            (status.enabled ? "AI provider ready" : "AI disabled")
          }
        >
          {status.provider}
          {status.enabled ? "" : " — safe fallback responses only."}
        </Alert>
      ) : null}
      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      {!loading ? (
        <Card className="max-w-2xl space-y-4">
          <Select
            label="Feature"
            value={feature}
            onChange={(e) => setFeature(e.target.value)}
          >
            {features.map((f) => (
              <option key={f.key} value={f.key}>
                {f.label}
                {f.enabled === false ? " (disabled)" : ""}
              </option>
            ))}
          </Select>
          {!features.length ? (
            <EmptyState
              title="No features"
              description="No admin AI features are available for your account."
            />
          ) : (
            <>
              <Textarea
                label="Notes (optional)"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
              />
              <Button onClick={() => void onGenerate()} disabled={busy || !feature}>
                {busy ? "Generating…" : "Generate draft"}
              </Button>
            </>
          )}
        </Card>
      ) : null}

      {result ? <SuggestionResult result={result} /> : null}
    </DashboardShell>
  );
}
