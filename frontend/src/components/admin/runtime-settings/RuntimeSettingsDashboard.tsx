"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RuntimeSettingSourceBadge } from "@/components/admin/runtime-settings/RuntimeSettingSourceBadge";
import { RuntimeSettingTestButton } from "@/components/admin/runtime-settings/RuntimeSettingTestButton";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  Alert,
  Badge,
  Button,
  Card,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  fetchRuntimeSettingsDashboard,
  type RuntimeSettingsCategorySummary,
  type RuntimeSettingsDashboard,
} from "@/lib/runtime-settings-api";
import {
  categoryPath,
  deriveCategoryStatus,
  formatCategoryLabel,
  isSpecialistCategory,
  specialistHrefFor,
} from "@/lib/runtime-settings-display";
import { getRuntimeSettingsCapabilities } from "@/lib/runtime-settings-permissions";

const FALLBACK_CARDS: RuntimeSettingsCategorySummary[] = [
  { category: "email", label: "Email", testable: true },
  { category: "push", label: "Push", testable: true },
  { category: "ai", label: "AI", testable: true },
  { category: "payments", label: "Payments", testable: true },
  { category: "storage", label: "Storage", testable: true },
  { category: "integrations", label: "Integrations", testable: true },
  { category: "system-status", label: "System status", testable: false },
];

export function RuntimeSettingsDashboard() {
  const { user } = useAuth();
  const caps = getRuntimeSettingsCapabilities(user);
  const [data, setData] = useState<RuntimeSettingsDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const dashboard = await fetchRuntimeSettingsDashboard();
    setData(dashboard);
  }, []);

  useEffect(() => {
    if (!caps.view) return;
    let active = true;
    void (async () => {
      try {
        const dashboard = await fetchRuntimeSettingsDashboard();
        if (!active) return;
        setData(dashboard);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError
            ? err.detail
            : "Failed to load runtime settings",
        );
        setData(null);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [caps.view]);

  if (!caps.view) {
    return (
      <Alert tone="danger" title="Permission denied">
        You need <code className="font-mono text-xs">admin.settings.view</code>{" "}
        to open Runtime Settings.
      </Alert>
    );
  }

  if (loading) {
    return <SkeletonLoader lines={8} />;
  }

  const categories =
    data?.categories && data.categories.length > 0
      ? data.categories
      : FALLBACK_CARDS;

  const system = data?.system;

  return (
    <div className="space-y-6">
      {error ? (
        <Alert
          tone="warning"
          title="Could not load dashboard"
          action={
            <Button type="button" size="sm" variant="secondary" onClick={() => void load()}>
              Retry
            </Button>
          }
        >
          {error}. Showing category links so you can still navigate.
        </Alert>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-muted-foreground">
          Optional runtime overrides and integration status. Boot-critical secrets
          stay in environment config. Email and Push secrets open their specialist
          editors.
        </p>
        <div className="flex flex-wrap gap-2">
          {caps.viewAudit ? (
            <Link href="/admin/settings/runtime/audit">
              <Button variant="secondary" size="sm">
                Audit history
              </Button>
            </Link>
          ) : null}
          {caps.viewAudit ? (
            <Link href="/admin/audit-logs?resource_type=runtime_setting">
              <Button variant="ghost" size="sm">
                Platform audit
              </Button>
            </Link>
          ) : null}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {categories.map((card) => (
          <CategoryCard
            key={card.category}
            card={card}
            canTest={caps.testIntegrations}
            canViewSystem={caps.viewSystemStatus}
          />
        ))}
      </div>

      {caps.viewSystemStatus && system ? (
        <Card className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-base font-bold text-heading">System status</h2>
            <Link href={categoryPath("system-status")}>
              <Button variant="ghost" size="sm">
                Open panel
              </Button>
            </Link>
          </div>
          <dl className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <StatusFact label="Version" value={system.version || "—"} />
            <StatusFact label="Build SHA" value={system.build_sha || "—"} mono />
            <StatusFact
              label="Last boot"
              value={formatDateTime(system.last_boot_at)}
            />
            <StatusFact label="App env" value={system.app_env || "—"} />
          </dl>
        </Card>
      ) : null}
    </div>
  );
}

function CategoryCard({
  card,
  canTest,
  canViewSystem,
}: {
  card: RuntimeSettingsCategorySummary;
  canTest: boolean;
  canViewSystem: boolean;
}) {
  const status = deriveCategoryStatus(card);
  const specialist = specialistHrefFor(card.category);
  const isSystem = card.category === "system-status";
  const href = isSystem
    ? canViewSystem
      ? categoryPath("system-status")
      : null
    : categoryPath(card.category);
  const editHref = specialist || href;
  const title = formatCategoryLabel(card.category, card.label);

  return (
    <Card className="flex h-full flex-col gap-4">
      <div className="space-y-2">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <h3 className="text-lg font-extrabold tracking-tight text-heading">
            {title}
          </h3>
          <Badge tone={status.tone} size="sm">
            {status.label}
          </Badge>
        </div>
        {card.provider ? (
          <p className="text-xs text-muted-foreground">
            Provider: <span className="font-medium text-foreground">{card.provider}</span>
          </p>
        ) : null}
        <RuntimeSettingSourceBadge
          source={card.source}
          item={{
            source: card.source || "default",
            status: card.status,
            configured: card.configured,
            enabled: card.enabled,
            is_secret: false,
            value: card.configured ? true : null,
          }}
        />
        <p className="text-xs text-muted-foreground">
          Updated {formatDateTime(card.last_updated_at)}
        </p>
        {isSpecialistCategory(card.category) ? (
          <p className="text-xs text-muted-foreground">
            Secrets managed on the specialist page — not duplicated here.
          </p>
        ) : null}
      </div>

      <div className="mt-auto flex flex-wrap gap-2">
        {editHref ? (
          <Link href={isSpecialistCategory(card.category) ? categoryPath(card.category) : editHref}>
            <Button size="sm" variant="dark">
              {isSpecialistCategory(card.category) ? "Open" : "Edit"}
            </Button>
          </Link>
        ) : (
          <Button size="sm" variant="secondary" disabled>
            No access
          </Button>
        )}
        {specialist ? (
          <Link href={specialist}>
            <Button size="sm" variant="secondary">
              Specialist
            </Button>
          </Link>
        ) : null}
        {card.testable !== false &&
        !isSystem &&
        ["email", "push", "ai", "payments", "storage", "integrations"].includes(
          card.category,
        ) ? (
          <RuntimeSettingTestButton
            category={card.category}
            disabled={!canTest}
            label="Test"
          />
        ) : null}
      </div>
    </Card>
  );
}

function StatusFact({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-[var(--radius-sm)] border border-border/70 bg-surface-muted/40 px-3 py-2 dark:bg-surface-inset/40">
      <dt className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd
        className={
          mono
            ? "mt-0.5 truncate font-mono text-xs text-foreground"
            : "mt-0.5 text-sm font-semibold text-foreground"
        }
      >
        {value}
      </dd>
    </div>
  );
}
