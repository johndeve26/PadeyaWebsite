"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Alert, SkeletonLoader, StatCard } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminBlogPostAnalytics } from "@/lib/analytics-api";
import type { AdminBlogPostAnalytics } from "@/lib/types/analytics";

import { StudioPanel } from "./BlogStudioShell";

export function BlogPostAnalyticsPanel({ postId }: { postId: string | null }) {
  const [data, setData] = useState<AdminBlogPostAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!postId) {
      setData(null);
      setError(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const next = await fetchAdminBlogPostAnalytics(postId);
        if (!cancelled) {
          setData(next);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setData(null);
          setError(
            err instanceof ApiError
              ? err.message
              : "Failed to load post analytics",
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [postId]);

  if (!postId) {
    return (
      <StudioPanel
        title="Analytics"
        description="Save the draft first to see post-level engagement."
      >
        <p className="text-sm text-muted-foreground">
          Analytics appear after the post exists.
        </p>
      </StudioPanel>
    );
  }

  return (
    <StudioPanel
      title="Analytics"
      description="Public engagement for this post (bots & internal-admin excluded)."
    >
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {!data && !error ? <SkeletonLoader lines={4} /> : null}
      {data ? (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <StatCard title="Views" value={data.totals.post_views} />
            <StatCard title="Unique" value={data.totals.unique_visitors} />
            <StatCard title="Shares" value={data.totals.shares} />
            <StatCard title="CTAs" value={data.totals.cta_clicks} />
          </div>
          <dl className="grid gap-2 text-sm">
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Read 50%</dt>
              <dd className="font-semibold">{data.rates.read_50_rate}%</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Read 100%</dt>
              <dd className="font-semibold">{data.rates.read_100_rate}%</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Comments</dt>
              <dd className="font-semibold">{data.totals.comments}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Draft → publish</dt>
              <dd className="font-semibold">
                {data.publishing.draft_age_hours != null
                  ? `${data.publishing.draft_age_hours}h`
                  : "—"}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">AI ops</dt>
              <dd className="font-semibold">
                {data.ai_studio.successes}/{data.ai_studio.operations}
              </dd>
            </div>
          </dl>
          <Link
            href="/admin/analytics/blog"
            className="text-sm font-semibold text-primary-text hover:underline"
          >
            Open blog analytics →
          </Link>
        </div>
      ) : null}
    </StudioPanel>
  );
}
