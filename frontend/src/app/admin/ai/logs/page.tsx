"use client";

import { useCallback, useEffect, useState } from "react";

import {
  AIControlCenterHeader,
  AIControlCenterNav,
} from "@/components/admin/ai/AIControlCenterNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Badge, Card, Input, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAISafeLogs } from "@/lib/ai-api";
import type { AISafeLog } from "@/lib/types/ai";

export default function AdminAILogsPage() {
  const [logs, setLogs] = useState<AISafeLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [feature, setFeature] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const load = useCallback(async () => {
    const data = await fetchAISafeLogs({
      limit: 60,
      feature_key: feature || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    });
    setLogs(data.items);
  }, [feature, dateFrom, dateTo]);

  useEffect(() => {
    void load()
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load logs"),
      )
      .finally(() => setLoading(false));
  }, [load]);

  return (
    <DashboardShell tone="soft" eyebrow="Admin" title="AI" description="">
      <div className="space-y-6">
        <AIControlCenterHeader
          title="Generation logs"
          description="Safe metadata only — no raw prompts, secrets, or private support bodies."
        />
        <AIControlCenterNav />

        <Card className="flex flex-wrap gap-3">
          <Input
            label="Feature key"
            value={feature}
            onChange={(e) => setFeature(e.target.value)}
          />
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
        </Card>

        {loading ? <SkeletonLoader lines={5} /> : null}
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}

        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="bg-surface-muted text-muted-foreground">
              <tr>
                <th className="px-3 py-2">Time</th>
                <th className="px-3 py-2">Feature</th>
                <th className="px-3 py-2">Actor</th>
                <th className="px-3 py-2">Provider</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Latency</th>
                <th className="px-3 py-2">Validation</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-t border-border">
                  <td className="px-3 py-2 whitespace-nowrap">
                    {log.created_at
                      ? new Date(log.created_at).toLocaleString()
                      : "—"}
                  </td>
                  <td className="px-3 py-2">{log.feature_key}</td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">
                    {log.actor_user_id?.slice(0, 8) ?? "—"}
                  </td>
                  <td className="px-3 py-2">
                    {log.provider}/{log.model ?? "—"}
                  </td>
                  <td className="px-3 py-2">
                    <Badge tone={log.status === "success" ? "accent" : "danger"}>
                      {log.status}
                    </Badge>
                    {log.used_fallback ? (
                      <Badge tone="warning" className="ml-1">
                        fallback
                      </Badge>
                    ) : null}
                  </td>
                  <td className="px-3 py-2">
                    {log.latency_ms != null ? `${log.latency_ms}ms` : "—"}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {log.validation_result ?? "—"}
                    {log.redaction_applied ? " · redacted" : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!logs.length && !loading ? (
            <p className="p-4 text-sm text-muted-foreground">No logs in this range.</p>
          ) : null}
        </div>
      </div>
    </DashboardShell>
  );
}
