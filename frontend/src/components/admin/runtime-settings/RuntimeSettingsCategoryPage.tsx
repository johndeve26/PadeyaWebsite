"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { RuntimeSettingField } from "@/components/admin/runtime-settings/RuntimeSettingField";
import { RuntimeSettingTestButton } from "@/components/admin/runtime-settings/RuntimeSettingTestButton";
import { SecretSettingField } from "@/components/admin/runtime-settings/SecretSettingField";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  sendEmailSettingsTest,
  fetchEmailProviderSettings,
} from "@/lib/email-api";
import { formatDateTime } from "@/lib/format";
import {
  testAdminPush,
  fetchAdminPushSettings,
} from "@/lib/notifications-api";
import {
  clearRuntimeSettingOverride,
  fetchRuntimeSettingsCategory,
  updateRuntimeSetting,
  type RuntimeSettingsCategoryResponse,
  type RuntimeSettingItem,
} from "@/lib/runtime-settings-api";
import {
  formatCategoryLabel,
  formatSecretDisplay,
  isSpecialistCategory,
  sanitizePublicMessage,
  specialistHrefFor,
} from "@/lib/runtime-settings-display";
import { getRuntimeSettingsCapabilities } from "@/lib/runtime-settings-permissions";

type Props = {
  category: string;
};

export function RuntimeSettingsCategoryPage({ category }: Props) {
  const { user } = useAuth();
  const caps = getRuntimeSettingsCapabilities(user);
  const toast = useToast();
  const [data, setData] = useState<RuntimeSettingsCategoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const isSystem = category === "system-status";
  const specialist = specialistHrefFor(category);
  const specialistMode = isSpecialistCategory(category);

  const canOpen =
    isSystem ? caps.viewSystemStatus : caps.view;
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (isSystem) {
      // System status may come from dashboard or category endpoint.
      const res = await fetchRuntimeSettingsCategory(category);
      setData(res);
      return;
    }
    if (specialistMode) {
      // Prefer specialist status for email/push; still try unified category GET.
      try {
        const res = await fetchRuntimeSettingsCategory(category);
        setData(res);
      } catch {
        if (category === "email") {
          const email = await fetchEmailProviderSettings();
          setData({
            category: "email",
            label: "Email",
            settings: [],
            specialist_href: "/admin/email/settings",
            provider: email.provider,
            configured: email.email_enabled && Boolean(email.smtp_host || email.provider),
            enabled: email.email_enabled,
            last_updated_at: email.updated_at,
            status: email.email_enabled ? "configured" : "disabled",
          });
        } else if (category === "push") {
          const push = await fetchAdminPushSettings();
          setData({
            category: "push",
            label: "Push",
            settings: [],
            specialist_href: "/admin/push/settings",
            provider: push.provider,
            configured: push.push_enabled && push.vapid_private_configured,
            enabled: push.push_enabled,
            last_updated_at: push.updated_at,
            status: push.push_enabled ? "configured" : "disabled",
          });
        } else {
          throw new Error("Category unavailable");
        }
      }
      return;
    }
    const res = await fetchRuntimeSettingsCategory(category);
    setData(res);
  }, [category, isSystem, specialistMode]);

  useEffect(() => {
    if (!canOpen) return;
    let active = true;
    void (async () => {
      try {
        await load();
        if (!active) return;
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError
            ? err.detail
            : "Failed to load category settings",
        );
        setData(null);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [canOpen, load]);

  const title = useMemo(
    () => formatCategoryLabel(category, data?.label),
    [category, data?.label],
  );

  async function saveValue(setting: RuntimeSettingItem, value: string | number | boolean | null) {
    setBusyKey(setting.key);
    setFieldErrors((prev) => {
      const next = { ...prev };
      delete next[setting.key];
      return next;
    });
    try {
      const updated = await updateRuntimeSetting(category, setting.key, { value });
      setData((prev) =>
        prev
          ? {
              ...prev,
              settings: prev.settings.map((s) =>
                s.key === setting.key ? { ...s, ...updated } : s,
              ),
            }
          : prev,
      );
      toast.push({ tone: "success", title: "Setting saved" });
      await load();
    } catch (err) {
      const msg = sanitizePublicMessage(
        err instanceof ApiError ? err.detail : "Could not save",
      );
      setFieldErrors((prev) => ({ ...prev, [setting.key]: msg }));
      toast.push({ tone: "danger", title: "Save failed", description: msg });
    } finally {
      setBusyKey(null);
    }
  }

  async function replaceSecret(setting: RuntimeSettingItem, secretValue: string) {
    setBusyKey(setting.key);
    setFieldErrors((prev) => {
      const next = { ...prev };
      delete next[setting.key];
      return next;
    });
    try {
      await updateRuntimeSetting(category, setting.key, {
        secret_value: secretValue,
      });
      toast.push({ tone: "success", title: "Secret updated" });
      await load();
    } catch (err) {
      const msg = sanitizePublicMessage(
        err instanceof ApiError ? err.detail : "Could not update secret",
      );
      setFieldErrors((prev) => ({ ...prev, [setting.key]: msg }));
      toast.push({ tone: "danger", title: "Secret update failed", description: msg });
    } finally {
      setBusyKey(null);
    }
  }

  async function clearOverride(setting: RuntimeSettingItem) {
    setBusyKey(setting.key);
    try {
      await clearRuntimeSettingOverride(category, setting.key);
      toast.push({
        tone: "success",
        title: "Override cleared",
        description: "Using environment fallback.",
      });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Clear failed",
        description: sanitizePublicMessage(
          err instanceof ApiError ? err.detail : "Could not clear override",
        ),
      });
    } finally {
      setBusyKey(null);
    }
  }

  if (!canOpen) {
    return (
      <Alert tone="danger" title="Permission denied">
        {isSystem
          ? "You need admin.settings.view_system_status (or view) for system status."
          : "You need admin.settings.view to open this category."}
      </Alert>
    );
  }

  if (loading) return <SkeletonLoader lines={8} />;

  return (
    <div className="space-y-5">
      {error ? (
        <Alert tone="danger" title="Failed to load">
          {error}
        </Alert>
      ) : null}

      {category === "ai" ? (
        <Alert tone="info" title="AI Control Center">
          For providers, per-feature routing, spend, and safety use{" "}
          <Link href="/admin/ai" className="font-semibold underline">
            /admin/ai
          </Link>
          . Fields below are advanced runtime env overrides for engineers.
        </Alert>
      ) : null}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-extrabold tracking-tight text-heading">
              {title}
            </h2>
            {data?.provider ? (
              <Badge tone="neutral" size="sm">
                {data.provider}
              </Badge>
            ) : null}
          </div>
          {data?.description ? (
            <p className="max-w-2xl text-sm text-muted-foreground">
              {data.description}
            </p>
          ) : null}
          <p className="text-xs text-muted-foreground">
            Last updated {formatDateTime(data?.last_updated_at)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/settings/runtime">
            <Button variant="ghost" size="sm">
              Back to hub
            </Button>
          </Link>
          {caps.viewAudit ? (
            <Link href="/admin/settings/runtime/audit">
              <Button variant="secondary" size="sm">
                Audit history
              </Button>
            </Link>
          ) : null}
          {specialist || data?.specialist_href ? (
            <Link href={specialist || data?.specialist_href || "#"}>
              <Button variant="dark" size="sm">
                Open specialist editor
              </Button>
            </Link>
          ) : null}
          {!isSystem ? (
            <RuntimeSettingTestButton
              category={category}
              disabled={!caps.testIntegrations}
              onTest={
                category === "email"
                  ? async () => {
                      const result = await sendEmailSettingsTest();
                      return {
                        ok: Boolean(result.ok),
                        message: result.error || result.status || undefined,
                      };
                    }
                  : category === "push"
                    ? async () => {
                        const result = await testAdminPush();
                        return {
                          ok: Boolean(result.ok),
                          message: result.message || result.status || undefined,
                        };
                      }
                    : undefined
              }
            />
          ) : null}
        </div>
      </div>

      {specialistMode ? (
        <Card className="space-y-3">
          <Alert tone="info" title="Specialist configuration">
            SMTP / VAPID secrets are managed on the existing{" "}
            <Link
              href={specialist || "#"}
              className="font-semibold underline-offset-2 hover:underline"
            >
              {category === "email" ? "Email settings" : "Push settings"}
            </Link>{" "}
            page. This hub does not write a second copy into runtime_settings.
          </Alert>
          <div className="flex flex-wrap gap-2">
            <Link href={specialist || "#"}>
              <Button variant="dark">Manage {title}</Button>
            </Link>
          </div>
          {data?.settings && data.settings.length > 0 ? (
            <p className="text-xs text-muted-foreground">
              Non-secret tunables below (if any) still use the runtime settings API.
            </p>
          ) : (
            <EmptyState
              title="No runtime overrides for this category"
              description="Use the specialist page for provider secrets and connection tests."
            />
          )}
        </Card>
      ) : null}

      {isSystem ? (
        <Card className="space-y-3">
          <Alert tone="info" title="Read-only">
            System status is display-only. Raw secrets are never shown.
          </Alert>
          {data?.settings?.length ? (
            <ul className="divide-y divide-border">
              {data.settings.map((setting) => (
                <li
                  key={setting.key}
                  className="flex flex-wrap items-center justify-between gap-2 py-3"
                >
                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      {setting.label}
                    </p>
                    <p className="font-mono text-[11px] text-muted-foreground">
                      {setting.key}
                    </p>
                  </div>
                  <div className="text-right text-sm">
                    {setting.is_secret ? (
                      <span>
                        {formatSecretDisplay({
                          configured: setting.configured,
                          masked_value: setting.masked_value,
                          first_four: setting.first_four,
                          last_four: setting.last_four,
                        })}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">
                        {setting.configured === false
                          ? "Not configured"
                          : String(setting.value ?? "—")}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="No status rows yet"
              description="When the API returns status items, they appear here without editable controls."
            />
          )}
        </Card>
      ) : null}

      {!isSystem && data?.settings && data.settings.length > 0 ? (
        <div className="space-y-4">
          {data.settings.map((setting) =>
            setting.is_secret || setting.fingerprint_display ? (
              <SecretSettingField
                key={setting.key}
                setting={setting}
                canEditSecrets={caps.editSecrets}
                canClear={caps.clearOverrides}
                busy={busyKey === setting.key}
                error={fieldErrors[setting.key] || null}
                onReplace={(secretValue) => replaceSecret(setting, secretValue)}
                onClearOverride={() => clearOverride(setting)}
              />
            ) : (
              <RuntimeSettingField
                key={setting.key}
                setting={setting}
                canEdit={caps.editRuntime}
                canClear={caps.clearOverrides}
                busy={busyKey === setting.key}
                error={fieldErrors[setting.key] || null}
                onSave={(value) => saveValue(setting, value)}
                onClearOverride={() => clearOverride(setting)}
              />
            ),
          )}
        </div>
      ) : null}

      {!isSystem &&
      !specialistMode &&
      (!data?.settings || data.settings.length === 0) &&
      !error ? (
        <EmptyState
          title="No runtime overrides available yet"
          description="This category has no allowlisted keys from the API. Env-only values may still appear under System status."
        />
      ) : null}

      {caps.viewAudit ? (
        <p className="text-xs text-muted-foreground">
          Changes write audit actions such as{" "}
          <code className="font-mono">runtime_setting_update</code>,{" "}
          <code className="font-mono">runtime_setting_reset</code>, and related
          runtime_setting_* events.{" "}
          <Link
            href="/admin/settings/runtime/audit"
            className="font-semibold underline-offset-2 hover:underline"
          >
            View audit history
          </Link>
          .
        </p>
      ) : null}
    </div>
  );
}
