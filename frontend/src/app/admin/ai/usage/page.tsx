"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

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
  Input,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAIUsageDashboard } from "@/lib/ai-api";
import type { AIUsageDashboard } from "@/lib/types/ai";

function microsToUsd(micros: number | null | undefined): string {
  if (micros == null) return "—";
  return `$${(micros / 1_000_000).toFixed(4)}`;
}

export default function AdminAIUsagePage() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [dash, setDash] = useState<AIUsageDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const params = {
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    };
    const usage = await fetchAIUsageDashboard(params);
    setDash(usage);
  }, [dateFrom, dateTo]);

  useEffect(() => {
    void load()
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load usage"),
      )
      .finally(() => setLoading(false));
  }, [load]);

  async function onRefresh() {
    setLoading(true);
    setError(null);
    try {
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load usage");
    } finally {
      setLoading(false);
    }
  }

  return (
    <DashboardShell tone="soft" eyebrow="Admin" title="AI" description="">
      <div className="space-y-6">
        <AIControlCenterHeader
          title="Usage"
          description="Aggregates by feature, provider, and actor. For row-level history see Logs."
        />
        <AIControlCenterNav />
        <Link href="/admin/ai/logs" className="text-sm font-semibold text-primary underline">
          Open generation logs
        </Link>

      <Card className="mb-4 flex flex-wrap items-end gap-3">
        <Input
          label="From"
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
        />
        <Input
          label="To"
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
        />
        <Button size="sm" onClick={() => void onRefresh()} disabled={loading}>
          Apply filters
        </Button>
      </Card>

      {loading && !dash ? <SkeletonLoader lines={5} /> : null}
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}

      {dash ? (
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <p className="text-xs text-muted-foreground">Total requests</p>
              <p className="text-2xl font-extrabold">{dash.total_requests}</p>
            </Card>
            <Card>
              <p className="text-xs text-muted-foreground">Success rate</p>
              <p className="text-2xl font-extrabold">
                {dash.success_rate != null ? `${dash.success_rate}%` : "—"}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-muted-foreground">Est. cost</p>
              <p className="text-2xl font-extrabold">
                {microsToUsd(dash.estimated_cost_micros)}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-muted-foreground">Avg latency</p>
              <p className="text-2xl font-extrabold">
                {dash.average_latency_ms != null
                  ? `${dash.average_latency_ms}ms`
                  : "—"}
              </p>
            </Card>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <p className="text-xs text-muted-foreground">Validation failures</p>
              <p className="text-xl font-extrabold">{dash.validation_failures}</p>
            </Card>
            <Card>
              <p className="text-xs text-muted-foreground">Redaction applied</p>
              <p className="text-xl font-extrabold">
                {dash.redaction_applied_count}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-muted-foreground">Fallback usage</p>
              <p className="text-xl font-extrabold">{dash.fallback_usage}</p>
            </Card>
            <Card>
              <p className="text-xs text-muted-foreground">Failures</p>
              <p className="text-xl font-extrabold">{dash.failure_count}</p>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="space-y-3">
              <h2 className="font-extrabold">By feature</h2>
              <ul className="space-y-2 text-sm">
                {dash.by_feature.slice(0, 12).map((row) => (
                  <li
                    key={row.feature_key}
                    className="flex justify-between gap-2 border-b border-border pb-1"
                  >
                    <span className="truncate">{row.feature_key}</span>
                    <span className="shrink-0 text-muted-foreground">
                      {row.requests} · {microsToUsd(row.cost_micros)}
                    </span>
                  </li>
                ))}
                {!dash.by_feature.length ? (
                  <li className="text-muted-foreground">No requests in range.</li>
                ) : null}
              </ul>
            </Card>
            <Card className="space-y-3">
              <h2 className="font-extrabold">By provider / model</h2>
              <ul className="space-y-2 text-sm">
                {dash.by_provider_model.map((row) => (
                  <li
                    key={`${row.provider}-${row.model}`}
                    className="flex justify-between gap-2 border-b border-border pb-1"
                  >
                    <span className="truncate">
                      {row.provider}/{row.model || "—"}
                    </span>
                    <span className="shrink-0 text-muted-foreground">
                      {row.requests} · {microsToUsd(row.cost_micros)}
                    </span>
                  </li>
                ))}
                {!dash.by_provider_model.length ? (
                  <li className="text-muted-foreground">No requests in range.</li>
                ) : null}
              </ul>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="space-y-3">
              <h2 className="font-extrabold">Top users</h2>
              <ul className="space-y-1 text-sm text-muted-foreground">
                {dash.top_users.map((u) => (
                  <li key={u.user_id}>
                    {u.user_id.slice(0, 8)}… — {u.requests}
                  </li>
                ))}
                {!dash.top_users.length ? <li>None</li> : null}
              </ul>
            </Card>
            <Card className="space-y-3">
              <h2 className="font-extrabold">Top hosts</h2>
              <ul className="space-y-1 text-sm text-muted-foreground">
                {dash.top_hosts.map((h) => (
                  <li key={h.host_id}>
                    {h.host_id.slice(0, 8)}… — {h.requests}
                  </li>
                ))}
                {!dash.top_hosts.length ? <li>None</li> : null}
              </ul>
            </Card>
          </div>
        </div>
      ) : null}
      </div>
    </DashboardShell>
  );
}
