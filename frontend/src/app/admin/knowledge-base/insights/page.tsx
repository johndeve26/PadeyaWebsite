"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button } from "@/components/ui";
import { ApiError, apiRequest } from "@/lib/api";

type FeedbackRow = {
  id: string;
  article_id: string;
  is_helpful: boolean;
  comment?: string | null;
  created_at: string;
};

type SearchTermRow = {
  query: string;
  hits: number;
  avg_results: number;
  last_seen?: string | null;
};

export default function AdminKnowledgeBaseInsightsPage() {
  const [feedback, setFeedback] = useState<FeedbackRow[]>([]);
  const [terms, setTerms] = useState<SearchTermRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [fb, st] = await Promise.all([
        apiRequest<FeedbackRow[]>("/admin/knowledge-base/feedback"),
        apiRequest<SearchTermRow[]>("/admin/knowledge-base/search-terms"),
      ]);
      setFeedback(fb);
      setTerms(st);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load insights");
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate
    void load();
  }, [load]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Content"
      title="Help insights"
      description="Helpful votes and safe search terms from the Help Center."
      actions={
        <Link href="/admin/knowledge-base">
          <Button size="sm" variant="ghost">
            Back
          </Button>
        </Link>
      }
    >
      {error ? <Alert tone="danger">{error}</Alert> : null}

      <section className="space-y-4">
        <h2 className="font-display text-xl font-extrabold text-heading">
          Search terms
        </h2>
        {terms.length ? (
          <ul className="divide-y divide-border border-t border-border">
            {terms.map((row) => (
              <li
                key={row.query}
                className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"
              >
                <span className="font-semibold text-heading">{row.query}</span>
                <span className="text-muted-foreground">
                  {row.hits} searches · avg {row.avg_results.toFixed(1)} results
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No search logs yet.</p>
        )}
      </section>

      <section className="mt-10 space-y-4">
        <h2 className="font-display text-xl font-extrabold text-heading">
          Recent feedback
        </h2>
        {feedback.length ? (
          <ul className="divide-y divide-border border-t border-border">
            {feedback.map((row) => (
              <li key={row.id} className="py-3 text-sm">
                <p className="font-semibold text-heading">
                  {row.is_helpful ? "Helpful" : "Not helpful"}
                </p>
                {row.comment ? (
                  <p className="mt-1 text-muted-foreground">{row.comment}</p>
                ) : null}
                <p className="mt-1 text-xs text-muted-foreground">
                  Article {row.article_id.slice(0, 8)}…
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No feedback yet.</p>
        )}
      </section>
    </DashboardShell>
  );
}
