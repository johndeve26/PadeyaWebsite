"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AdminAnalyticsSubnav } from "@/components/analytics/AdminAnalyticsSubnav";
import { TrendPanel } from "@/components/analytics/TrendPanel";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  DataTable,
  SectionHeader,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminBlogAnalytics } from "@/lib/analytics-api";
import type { AdminBlogAnalyticsSummary } from "@/lib/types/analytics";

export default function AdminBlogAnalyticsPage() {
  const [data, setData] = useState<AdminBlogAnalyticsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const summary = await fetchAdminBlogAnalytics();
        if (active) setData(summary);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load blog analytics",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin analytics"
      title="Blog"
      description="Engagement funnel, publishing cadence, and AI Studio usage — bots and internal-admin traffic excluded by default."
      actions={
        <Link href="/admin/blog">
          <Button variant="secondary">Manage posts</Button>
        </Link>
      }
    >
      <AdminAnalyticsSubnav />

      {error ? <Alert tone="danger">{error}</Alert> : null}
      {!data && !error ? <SkeletonLoader lines={8} /> : null}

      {data ? (
        <div className="space-y-8">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard title="Post views" value={data.totals.post_views} />
            <StatCard
              title="Unique visitors"
              value={data.totals.unique_visitors}
            />
            <StatCard title="Shares" value={data.totals.shares} />
            <StatCard title="CTA clicks" value={data.totals.cta_clicks} />
          </div>

          <section className="space-y-3">
            <SectionHeader
              title="Engagement funnel"
              description="Index → cards → article → read depth → engagement"
            />
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <StatCard
                title="Card CTR"
                value={`${data.funnel.click_through_rate}%`}
              />
              <StatCard
                title="Read 50% rate"
                value={`${data.funnel.read_50_rate}%`}
              />
              <StatCard
                title="Share rate"
                value={`${data.funnel.share_rate}%`}
              />
            </div>
            <DataTable
              rowKey={(r) => r.step}
              columns={[
                { key: "step", header: "Step", cell: (r) => r.step },
                { key: "count", header: "Count", cell: (r) => r.count },
              ]}
              rows={[
                { step: "Index views", count: data.funnel.index_views },
                {
                  step: "Card impressions",
                  count: data.funnel.card_impressions,
                },
                { step: "Card clicks", count: data.funnel.card_clicks },
                { step: "Post views", count: data.funnel.post_views },
                { step: "Scroll ≥50%", count: data.funnel.scroll_50 },
                {
                  step: "Engaged (share/CTA/related/comment)",
                  count: data.funnel.engaged,
                },
              ]}
            />
          </section>

          <TrendPanel
            title="Views over time"
            points={data.timeseries.map((p) => ({
              label: p.date,
              value: p.post_views,
              display: String(p.post_views),
            }))}
            emptyTitle="No blog views in range"
          />

          <section className="space-y-3">
            <SectionHeader title="Top posts" description="By public post views" />
            <DataTable
              rowKey={(p) => p.post_id}
              emptyTitle="No post views yet"
              columns={[
                {
                  key: "title",
                  header: "Post",
                  primary: true,
                  cell: (p) => (
                    <Link
                      href={`/admin/blog/${p.post_id}/edit`}
                      className="font-semibold text-primary-text hover:underline"
                    >
                      {p.title}
                    </Link>
                  ),
                },
                { key: "views", header: "Views", cell: (p) => p.views },
                { key: "shares", header: "Shares", cell: (p) => p.shares },
                { key: "cta", header: "CTAs", cell: (p) => p.cta_clicks },
                {
                  key: "comments",
                  header: "Comments",
                  cell: (p) => p.comments,
                },
              ]}
              rows={data.top_posts}
            />
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="space-y-3">
              <SectionHeader
                title="Publishing"
                description="Cadence and draft-to-publish time"
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <StatCard
                  title="Published"
                  value={data.publishing.posts_published}
                />
                <StatCard
                  title="Avg draft age (hrs)"
                  value={
                    data.publishing.avg_draft_age_hours != null
                      ? data.publishing.avg_draft_age_hours
                      : "—"
                  }
                />
              </div>
            </section>
            <section className="space-y-3">
              <SectionHeader
                title="AI Studio"
                description="Operations only — no prompts stored"
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <StatCard
                  title="Operations"
                  value={data.ai_studio.operations}
                />
                <StatCard
                  title="Success rate"
                  value={`${data.ai_studio.success_rate}%`}
                />
              </div>
              <DataTable
                rowKey={(r) => r.operation}
                emptyTitle="No AI Studio ops in range"
                columns={[
                  {
                    key: "operation",
                    header: "Operation",
                    cell: (r) => r.operation,
                  },
                  { key: "count", header: "Count", cell: (r) => r.count },
                ]}
                rows={data.ai_studio.by_operation}
              />
            </section>
          </div>

          <Alert tone="info" title="Traffic separation">
            Bot events: {data.totals.bot_events}. Internal-admin events:{" "}
            {data.totals.internal_admin_events}. Public totals exclude both.
          </Alert>
        </div>
      ) : null}
    </DashboardShell>
  );
}
