"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Badge, Button, Card, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchProductionReadiness,
  type AIReadinessSummary,
  type ProductionReadinessReport,
  type ReadinessCheck,
} from "@/lib/readiness-api";

const CATEGORY_LABELS: Record<string, string> = {
  environment: "Environment",
  database: "Database",
  demo_data: "Demo data",
  integrations: "Integrations",
  infrastructure: "Infrastructure",
  operations: "Operations",
  ai: "AI (Pàdéyá Copilot)",
};

function aiStatusTone(status: AIReadinessSummary["status"]) {
  switch (status) {
    case "PASS":
      return "accent" as const;
    case "FAIL":
      return "danger" as const;
    default:
      return "outline" as const;
  }
}

function statusTone(status: ReadinessCheck["status"]) {
  switch (status) {
    case "pass":
      return "accent" as const;
    case "fail":
      return "danger" as const;
    case "warn":
      return "outline" as const;
    default:
      return "outline" as const;
  }
}

export function AdminGoLiveReadinessPage() {
  const [report, setReport] = useState<ProductionReadinessReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProductionReadiness();
      setReport(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load readiness report");
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const grouped = useMemo(() => {
    if (!report) return [];
    const map = new Map<string, ReadinessCheck[]>();
    for (const check of report.checks) {
      const list = map.get(check.category) ?? [];
      list.push(check);
      map.set(check.category, list);
    }
    return [...map.entries()];
  }, [report]);

  const failCount = report?.checks.filter((c) => c.status === "fail").length ?? 0;
  const warnCount = report?.checks.filter((c) => c.status === "warn").length ?? 0;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Platform"
      title="Go live"
      description="Read-only preflight for Pàdéyá production — environment, demo data, integrations, migrations, and AI readiness. Does not change any data."
      actions={
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" disabled={loading} onClick={() => void load()}>
            Refresh
          </Button>
          <Link href="/admin/platform/maintenance">
            <Button size="sm" variant="ghost">
              Maintenance
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}

      {loading && !report ? (
        <SkeletonLoader className="h-40 w-full rounded-xl" />
      ) : null}

      {report ? (
        <div className="space-y-6">
          <Card
            padded
            className={
              report.verdict === "READY_FOR_PRODUCTION"
                ? "border-accent/40 bg-accent/5"
                : "border-destructive/40 bg-destructive/5"
            }
          >
            <div className="flex flex-wrap items-center gap-3">
              <Badge
                tone={report.verdict === "READY_FOR_PRODUCTION" ? "accent" : "danger"}
                size="md"
              >
                {report.verdict === "READY_FOR_PRODUCTION"
                  ? "Ready for production"
                  : "Blocked"}
              </Badge>
              <p className="text-sm text-muted-foreground">{report.summary}</p>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              {failCount} blocking · {warnCount} warning
              {warnCount === 1 ? "" : "s"} · Run{" "}
              <code className="rounded bg-muted px-1 py-0.5 font-mono text-[11px]">
                PYTHONPATH=. python scripts/prod_preflight.py
              </code>{" "}
              from <code className="font-mono text-[11px]">backend/</code> on the server for
              the same checks in CI/SSH.
            </p>
          </Card>

          <Alert tone="info" title="Backup reminder">
            Schedule{" "}
            <code className="font-mono text-xs">./scripts/prod-backup-db.sh</code> before
            go-live and after migrations. Never copy a local demo database to production.
          </Alert>

          {report.ai_readiness ? (
            <Card padded className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-sm font-extrabold uppercase tracking-wide text-muted-foreground">
                  AI readiness
                </h2>
                <Badge tone={aiStatusTone(report.ai_readiness.status)} size="sm">
                  AI_READY: {report.ai_readiness.status}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">{report.ai_readiness.message}</p>
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-semibold text-foreground">Templates (24)</dt>
                  <dd className="text-muted-foreground">
                    {report.ai_readiness.templates_seeded ? "Seeded" : "Missing — see AI checks"}
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold text-foreground">Feature routes</dt>
                  <dd className="text-muted-foreground">
                    {report.ai_readiness.feature_routes_present
                      ? "Present"
                      : "Incomplete — open AI Control Center"}
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold text-foreground">Providers</dt>
                  <dd className="text-muted-foreground">{report.ai_readiness.provider_status}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-foreground">Kill switch</dt>
                  <dd className="text-muted-foreground">
                    {report.ai_readiness.kill_switch_active
                      ? "AI_KILL_SWITCH active (AI disabled)"
                      : "Off"}
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold text-foreground">Blocked keys</dt>
                  <dd className="text-muted-foreground">{report.ai_readiness.blocked_keys_status}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-foreground">Quarantined keys</dt>
                  <dd className="text-muted-foreground">
                    {report.ai_readiness.quarantined_keys_status}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-semibold text-foreground">Spend cap</dt>
                  <dd className="text-muted-foreground">{report.ai_readiness.spend_cap_status}</dd>
                </div>
              </dl>
              <Link href="/admin/ai/features">
                <Button size="sm" variant="ghost">
                  Open AI Control Center
                </Button>
              </Link>
            </Card>
          ) : null}

          {grouped.map(([category, checks]) => (
            <section key={category} className="space-y-3">
              <h2 className="text-sm font-extrabold uppercase tracking-wide text-muted-foreground">
                {CATEGORY_LABELS[category] ?? category}
              </h2>
              <ul className="space-y-2">
                {checks.map((check) => (
                  <li key={check.id}>
                    <Card padded className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={statusTone(check.status)} size="sm">
                          {check.status.toUpperCase()}
                        </Badge>
                        <span className="font-semibold text-foreground">{check.name}</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{check.message}</p>
                      {check.fix && check.status !== "pass" ? (
                        <p className="text-sm text-foreground">
                          <span className="font-semibold">Fix: </span>
                          {check.fix}
                        </p>
                      ) : null}
                    </Card>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      ) : null}
    </DashboardShell>
  );
}
