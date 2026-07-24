"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  AIControlCenterHeader,
  AIControlCenterNav,
} from "@/components/admin/ai/AIControlCenterNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAIAdminOverview } from "@/lib/ai-api";
import type { AIAdminOverview } from "@/lib/types/ai";

function microsToUsd(micros: number | null | undefined): string {
  if (micros == null) return "—";
  return `$${(micros / 1_000_000).toFixed(2)}`;
}

export default function AdminAIHubPage() {
  const [overview, setOverview] = useState<AIAdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void fetchAIAdminOverview()
      .then(setOverview)
      .catch((err) =>
        setError(
          err instanceof ApiError ? err.detail : "Failed to load AI Control Center",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  const g = overview?.global_ai;
  const cc = overview?.control_center;
  const spend = overview?.spend;

  return (
    <DashboardShell tone="soft" eyebrow="Admin" title="AI" description="">
      <div className="space-y-6">
        <AIControlCenterHeader
          title="Overview"
          description="Global status, provider health, feature routing, spend, and safety at a glance."
        />
        <AIControlCenterNav />

        {loading ? <SkeletonLoader lines={4} /> : null}
        {error ? (
          <Alert tone="danger" title="Could not load">
            {error}
          </Alert>
        ) : null}

        {overview && g ? (
          <>
            <div className="grid gap-4 lg:grid-cols-3">
              <Card className="space-y-3 lg:col-span-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-extrabold">Global AI</h2>
                  <Badge
                    tone={
                      g.disabled_by_environment
                        ? "danger"
                        : g.enabled
                          ? "accent"
                          : "warning"
                    }
                  >
                    {g.status_label}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  {g.disabled_by_environment
                    ? "AI_KILL_SWITCH is active. Cannot enable from the UI."
                    : g.enabled
                      ? "AI is on for enabled features."
                      : "AI is off — template drafts may still apply where allowed."}
                </p>
              </Card>

              <Card className="space-y-2">
                <h2 className="font-extrabold">Providers</h2>
                <p className="text-3xl font-extrabold">
                  {cc?.providers_enabled ?? 0}
                  <span className="text-base font-normal text-muted-foreground">
                    {" "}
                    / {cc?.providers_configured ?? 0} configured
                  </span>
                </p>
                <p className="text-xs text-muted-foreground">
                  {cc?.providers_healthy ?? 0} healthy · {cc?.routing_gaps ?? 0}{" "}
                  routing gaps
                </p>
                <Link href="/admin/ai/providers">
                  <Button size="sm" variant="secondary">
                    Manage providers
                  </Button>
                </Link>
              </Card>

              <Card className="space-y-2">
                <h2 className="font-extrabold">Features enabled</h2>
                <p className="text-3xl font-extrabold">{cc?.features_enabled ?? 0}</p>
                <Link href="/admin/ai/features">
                  <Button size="sm" variant="secondary">
                    Feature routing
                  </Button>
                </Link>
              </Card>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Card>
                <p className="text-xs text-muted-foreground">Requests this month</p>
                <p className="text-2xl font-extrabold">
                  {cc?.requests_this_month ?? 0}
                </p>
                <p className="text-xs text-muted-foreground">
                  Success {cc?.success_rate_pct != null ? `${cc.success_rate_pct}%` : "—"}
                </p>
              </Card>
              <Card>
                <p className="text-xs text-muted-foreground">Est. spend</p>
                <p className="text-2xl font-extrabold">
                  {microsToUsd(cc?.estimated_cost_micros)}
                </p>
                <p className="text-xs text-muted-foreground">
                  Cap {microsToUsd(spend?.spent_micros_this_month)} /{" "}
                  {spend?.monthly_spend_cap_micros != null
                    ? microsToUsd(spend.monthly_spend_cap_micros)
                    : "none"}
                </p>
              </Card>
              <Card>
                <p className="text-xs text-muted-foreground">Avg latency</p>
                <p className="text-2xl font-extrabold">
                  {cc?.average_latency_ms != null
                    ? `${cc.average_latency_ms}ms`
                    : "—"}
                </p>
              </Card>
              <Card>
                <p className="text-xs text-muted-foreground">Quality signals</p>
                <p className="text-sm text-muted-foreground">
                  Validation failures {cc?.validation_failures ?? 0} · Redactions{" "}
                  {cc?.redaction_applied_count ?? 0} · Fallbacks{" "}
                  {cc?.fallback_usage ?? 0}
                </p>
              </Card>
            </div>

            <div className="flex flex-wrap gap-2">
              <Link href="/admin/ai/usage">
                <Button variant="secondary">View usage</Button>
              </Link>
              <Link href="/admin/ai/logs">
                <Button variant="secondary">View logs</Button>
              </Link>
              <Link href="/admin/ai/safety">
                <Button variant="secondary">Safety settings</Button>
              </Link>
              <Link href="/admin/ai/playground">
                <Button variant="ghost">Playground</Button>
              </Link>
            </div>
          </>
        ) : null}
      </div>
    </DashboardShell>
  );
}
