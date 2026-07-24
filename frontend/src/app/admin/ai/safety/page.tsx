"use client";

import { useEffect, useState } from "react";

import {
  AIControlCenterHeader,
  AIControlCenterNav,
} from "@/components/admin/ai/AIControlCenterNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Badge, Card, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAISafetyOverview } from "@/lib/ai-api";
import type { AISafetyOverview } from "@/lib/types/ai";

export default function AdminAISafetyPage() {
  const [data, setData] = useState<AISafetyOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void fetchAISafetyOverview()
      .then(setData)
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load safety"),
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <DashboardShell tone="soft" eyebrow="Admin" title="AI" description="">
      <div className="space-y-6">
        <AIControlCenterHeader
          title="Safety"
          description="Kill switch, redaction, validation, and product rules — AI stays draft-only."
        />
        <AIControlCenterNav />

        {loading ? <SkeletonLoader lines={4} /> : null}
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}

        {data ? (
          <>
            <Card className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="font-extrabold">Platform status</h2>
                <Badge tone={data.kill_switch_active ? "danger" : "accent"}>
                  {data.status_label}
                </Badge>
              </div>
              {data.api_key_banner ? (
                <Alert tone="info" title="API keys">
                  {data.api_key_banner}
                </Alert>
              ) : null}
              <ul className="grid gap-2 sm:grid-cols-2 text-sm text-muted-foreground">
                <li>Redaction: {data.redaction_enabled ? "On" : "Off"}</li>
                <li>Output validation: {data.output_validation_enabled ? "On" : "Off"}</li>
                <li>Human review default: {data.human_review_default ? "Yes" : "No"}</li>
                <li>Audit logging: {data.audit_logging_enabled ? "On" : "Off"}</li>
              </ul>
              <p className="text-xs text-muted-foreground">{data.retention_policy}</p>
            </Card>

            <Card className="space-y-2">
              <h2 className="font-extrabold">Product rules (never automatic)</h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                {data.product_rules.map((rule) => (
                  <li key={rule}>{rule}</li>
                ))}
              </ul>
            </Card>

            <Card className="space-y-2">
              <h2 className="font-extrabold">Denylisted context</h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                {data.denylisted_data_classes.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </Card>

            <Card className="space-y-2">
              <h2 className="font-extrabold">Disabled / env-blocked features</h2>
              <p className="text-sm text-muted-foreground">
                {data.enabled_feature_count} enabled of {data.total_managed_features}{" "}
                managed keys.
              </p>
              {data.env_disabled_features.length ? (
                <p className="text-xs">Env: {data.env_disabled_features.join(", ")}</p>
              ) : null}
            </Card>
          </>
        ) : null}
      </div>
    </DashboardShell>
  );
}
