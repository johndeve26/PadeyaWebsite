"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  AIControlCenterHeader,
  AIControlCenterNav,
} from "@/components/admin/ai/AIControlCenterNav";
import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  Input,
  PageToolbar,
  Select,
  SkeletonLoader,
  Switch,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAIAdminOverview,
  testAIConnection,
  updateAIAdminSettings,
  updateAISpendSettings,
} from "@/lib/ai-api";
import { userHasPermission } from "@/lib/auth/permissions";
import type {
  AIAdminOverview,
  AITestConnectionResult,
} from "@/lib/types/ai";

function microsToUsd(micros: number | null | undefined): string {
  if (micros == null) return "";
  return (micros / 1_000_000).toFixed(4);
}

function usdToMicros(usd: string): number | null {
  const n = Number(usd);
  if (!Number.isFinite(n) || n < 0) return null;
  return Math.round(n * 1_000_000);
}

export default function AdminAISettingsPage() {
  const { user } = useAuth();
  const canManageSettings = userHasPermission(
    user,
    "admin.ai.manage_settings",
    "admin.settings.edit_runtime",
  );
  const canManageSpend = userHasPermission(
    user,
    "admin.ai.manage_spend",
    "admin.ai.manage_settings",
    "admin.settings.edit_runtime",
  );
  const canTestConnection = userHasPermission(
    user,
    "admin.ai.test_connection",
    "admin.ai.manage_settings",
    "admin.settings.edit_runtime",
  );
  const [overview, setOverview] = useState<AIAdminOverview | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [provider, setProvider] = useState("template");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [capUsd, setCapUsd] = useState("");
  const [warningPct, setWarningPct] = useState("80");
  const [hardPct, setHardPct] = useState("100");
  const [hardStop, setHardStop] = useState(true);
  const [allowFallback, setAllowFallback] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<AITestConnectionResult | null>(
    null,
  );

  const apply = useCallback((data: AIAdminOverview) => {
    setOverview(data);
    setEnabled(data.global_ai.ai_enabled_setting);
    setProvider(data.provider.provider);
    setModel(data.provider.model);
    setBaseUrl(data.provider.base_url);
    setCapUsd(
      data.spend.monthly_spend_cap_micros != null
        ? microsToUsd(data.spend.monthly_spend_cap_micros)
        : "",
    );
    setWarningPct(String(data.spend.warning_threshold_pct));
    setHardPct(String(data.spend.hard_stop_threshold_pct));
    setHardStop(data.spend.hard_stop_enabled);
    setAllowFallback(data.spend.allow_template_fallback_when_capped);
  }, []);

  const load = useCallback(async () => {
    const data = await fetchAIAdminOverview();
    apply(data);
  }, [apply]);

  useEffect(() => {
    void load()
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load"),
      )
      .finally(() => setLoading(false));
  }, [load]);

  async function saveProvider() {
    if (!canManageSettings) {
      setError(
        "You need admin.ai.manage_settings (or admin.settings.edit_runtime) to change global AI settings.",
      );
      return;
    }
    setSaving(true);
    setError(null);
    setNote(null);
    try {
      const data = await updateAIAdminSettings({
        enabled: kill ? undefined : enabled,
        provider,
        model: model.trim() || undefined,
        base_url: baseUrl.trim() || undefined,
      });
      apply(data);
      setNote("Provider settings saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function saveSpend() {
    if (!canManageSpend) {
      setError(
        "You need admin.ai.manage_spend or admin.ai.manage_settings to change spend caps.",
      );
      return;
    }
    setSaving(true);
    setError(null);
    setNote(null);
    try {
      const clearCap = !capUsd.trim();
      const micros = clearCap ? null : usdToMicros(capUsd);
      if (!clearCap && micros == null) {
        setError("Enter a valid monthly spend cap in USD, or leave blank.");
        setSaving(false);
        return;
      }
      await updateAISpendSettings({
        clear_cap: clearCap,
        monthly_spend_cap_micros: clearCap ? undefined : micros,
        warning_threshold_pct: Number(warningPct) || 80,
        hard_stop_threshold_pct: Number(hardPct) || 100,
        hard_stop_enabled: hardStop,
        allow_template_fallback_when_capped: allowFallback,
      });
      await load();
      setNote("Spend controls saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Spend save failed");
    } finally {
      setSaving(false);
    }
  }

  async function onTest() {
    if (!canTestConnection) {
      setError(
        "You need admin.ai.test_connection (or manage settings) to run a connection test.",
      );
      return;
    }
    setTesting(true);
    setError(null);
    setTestResult(null);
    try {
      setTestResult(await testAIConnection());
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Test failed");
    } finally {
      setTesting(false);
    }
  }

  const kill = overview?.global_ai.disabled_by_environment;

  return (
    <DashboardShell tone="soft" eyebrow="Admin" title="AI" description="">
      <div className="space-y-6">
        <AIControlCenterHeader
          title="Settings"
          description="Global switch and platform spend. Provider profiles live under Providers."
        />
        <AIControlCenterNav />

        <Alert tone="info" title="Advanced runtime settings">
          Low-level env-backed knobs remain at{" "}
          <Link href="/admin/settings/runtime/ai" className="font-semibold underline">
            Runtime → AI
          </Link>{" "}
          for engineers. Operators should use this Control Center first.
        </Alert>

        {!canManageSettings ? (
          <Alert tone="warning" title="View only">
            You can review AI settings but cannot save changes. Ask a super admin to
            grant{" "}
            <span className="font-semibold">admin.ai.manage_settings</span> on your
            admin team role, or use an account with{" "}
            <span className="font-semibold">admin.settings.edit_runtime</span>.
          </Alert>
        ) : null}

      {loading ? <SkeletonLoader lines={5} /> : null}
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Saved">
          {note}
        </Alert>
      ) : null}

      {overview ? (
        <div className="space-y-6">
          <Card className="max-w-2xl space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-extrabold">Global AI</h2>
              <Badge tone={kill ? "danger" : enabled ? "accent" : "warning"}>
                {overview.global_ai.status_label}
              </Badge>
            </div>
            {kill ? (
              <Alert tone="danger" title="Disabled by environment">
                AI_KILL_SWITCH is active. You cannot enable AI from this UI.
              </Alert>
            ) : (
              <Switch
                checked={enabled}
                onCheckedChange={setEnabled}
                label="Enable AI globally"
                disabled={!canManageSettings}
              />
            )}
            <Select
              label="Provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              disabled={!canManageSettings}
            >
              {(overview.provider.allowed_providers.length
                ? overview.provider.allowed_providers
                : ["template", "openai", "anthropic", "gemini", "grok", "none"]
              ).map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </Select>
            <Input
              label="Model"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={!canManageSettings}
            />
            <Input
              label="Base URL"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              hint="OpenAI-compatible base URL for the selected provider."
              disabled={!canManageSettings}
            />
            <div className="rounded-lg border border-border bg-muted/30 p-3 text-sm text-muted-foreground">
              API key:{" "}
              {overview.api_key.configured
                ? `configured ${overview.api_key.masked ?? ""} (env-only, read-only)`
                : "not configured (env-only)"}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => void saveProvider()}
                disabled={saving || !canManageSettings}
              >
                {saving ? "Saving…" : "Save provider settings"}
              </Button>
              <Button
                variant="secondary"
                onClick={() => void onTest()}
                disabled={testing || !canTestConnection}
              >
                {testing ? "Testing…" : "Test connection"}
              </Button>
            </div>
            {testResult ? (
              <Alert
                tone={testResult.ok ? "success" : "warning"}
                title={testResult.ok ? "Connection OK" : "Connection issue"}
              >
                {testResult.message} · {testResult.provider}/{testResult.model}
                {testResult.latency_ms != null
                  ? ` · ${testResult.latency_ms}ms`
                  : ""}
                {testResult.used_fallback ? " · used fallback" : ""}
              </Alert>
            ) : null}
          </Card>

          <Card className="max-w-2xl space-y-4">
            <h2 className="text-lg font-extrabold">Spend controls</h2>
            <Input
              label="Monthly spend cap (USD)"
              value={capUsd}
              onChange={(e) => setCapUsd(e.target.value)}
              hint="Leave blank for unlimited. Soft warning / hard stop use thresholds below."
              disabled={!canManageSpend}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Warning threshold %"
                value={warningPct}
                onChange={(e) => setWarningPct(e.target.value)}
                disabled={!canManageSpend}
              />
              <Input
                label="Hard stop threshold %"
                value={hardPct}
                onChange={(e) => setHardPct(e.target.value)}
                disabled={!canManageSpend}
              />
            </div>
            <Switch
              checked={hardStop}
              onCheckedChange={setHardStop}
              label="Enable hard stop at threshold"
              disabled={!canManageSpend}
            />
            <Switch
              checked={allowFallback}
              onCheckedChange={setAllowFallback}
              label="Allow template fallback when capped"
              disabled={!canManageSpend}
            />
            <p className="text-sm text-muted-foreground">
              Spent this month: $
              {microsToUsd(overview.spend.spent_micros_this_month) || "0"}
              {overview.spend.spend_pct_of_cap != null
                ? ` (${overview.spend.spend_pct_of_cap}% of cap)`
                : ""}
            </p>
            <Button onClick={() => void saveSpend()} disabled={saving || !canManageSpend}>
              Save spend controls
            </Button>
          </Card>
        </div>
      ) : null}
      </div>
    </DashboardShell>
  );
}
