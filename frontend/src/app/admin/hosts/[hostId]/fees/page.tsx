"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { FeePreviewCalculator } from "@/components/admin/FeePreviewCalculator";
import {
  HostFeeOverrideForm,
  emptyOverrideForm,
  type OverrideFormState,
} from "@/components/admin/HostFeeOverrideForm";
import {
  datetimeLocalToIso,
  fixedMajorToMinor,
} from "@/components/admin/FeeSettingForm";
import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  DataTable,
  EmptyState,
  SectionHeader,
  SkeletonLoader,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { formatDateTime } from "@/lib/format";
import { formatFeeRate, resolveActiveFees } from "@/lib/fee-preview";
import {
  createHostFeeOverride,
  fetchFeeSettings,
  fetchHostFeeOverrides,
  updateHostFeeOverride,
} from "@/lib/fees-api";
import { fetchAdminVerifications } from "@/lib/hosts-lifecycle-api";
import type { HostFeeOverride, PlatformFeeSetting } from "@/lib/types/fees";

export default function AdminHostFeesPage() {
  const params = useParams();
  const hostId = String(params.hostId ?? "");
  const { user } = useAuth();
  const toast = useToast();

  const canView = userHasPermission(
    user,
    "admin.finance.view_fees",
    "admin.finance.manage_host_overrides",
    "admin.full_access",
  );
  const canManage = userHasPermission(
    user,
    "admin.finance.manage_host_overrides",
    "admin.full_access",
  );

  const [settings, setSettings] = useState<PlatformFeeSetting[]>([]);
  const [overrides, setOverrides] = useState<HostFeeOverride[] | null>(null);
  const [hostName, setHostName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<OverrideFormState>(emptyOverrideForm(hostId));
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [feeSettings, hostOverrides, verifications] = await Promise.all([
      fetchFeeSettings({ include_disabled: false }),
      fetchHostFeeOverrides({ host_id: hostId, include_disabled: true }),
      fetchAdminVerifications().catch(() => []),
    ]);
    setSettings(feeSettings);
    setOverrides(hostOverrides);
    const match = verifications.find((v) => v.host_id === hostId);
    setHostName(match?.host_display_name?.trim() || null);
    setForm(emptyOverrideForm(hostId));
  }, [hostId]);

  useEffect(() => {
    if (!canView || !hostId) return;
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load host fees",
          );
          setOverrides([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [canView, hostId, load]);

  const activeGlobals = useMemo(
    () => resolveActiveFees(settings, [], null),
    [settings],
  );

  async function onCreate() {
    setBusy(true);
    setError(null);
    try {
      await createHostFeeOverride({
        host_id: hostId,
        fee_key: form.fee_key,
        percentage_value: form.percentage_value.trim() || null,
        fixed_value: fixedMajorToMinor(form.fixed_value_major),
        payer: form.payer,
        enabled: form.enabled,
        effective_from: datetimeLocalToIso(form.effective_from),
        effective_to: form.effective_to
          ? datetimeLocalToIso(form.effective_to)
          : null,
        reason: form.reason.trim() || null,
      });
      toast.push({ tone: "success", title: "Override created" });
      setShowCreate(false);
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to create override",
      );
    } finally {
      setBusy(false);
    }
  }

  async function disableOverride(id: string) {
    setBusy(true);
    try {
      await updateHostFeeOverride(id, { enabled: false });
      toast.push({ tone: "success", title: "Override disabled" });
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to disable override",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!canView) {
    return (
      <DashboardShell tone="soft" eyebrow="Admin" title="Host fees">
        <Alert tone="warning">
          Missing permission <code>admin.finance.view_fees</code>.
        </Alert>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Host fees"
      title={hostName ?? "Host fee overrides"}
      description={`Custom rates for host ${hostId}. Overrides beat global fees when enabled.`}
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/finance/host-overrides">
            <Button variant="ghost">All overrides</Button>
          </Link>
          {canManage ? (
            <Button onClick={() => setShowCreate((v) => !v)}>
              {showCreate ? "Close" : "Add override"}
            </Button>
          ) : null}
        </div>
      }
    >
      <div className="space-y-6">
        {error ? <Alert tone="danger">{error}</Alert> : null}

        <Card className="space-y-3 p-5">
          <SectionHeader
            title="Active global fees"
            description="Defaults that apply when this host has no override."
          />
          {activeGlobals.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No enabled global fees.
            </p>
          ) : (
            <ul className="divide-y divide-border rounded-lg border border-border">
              {activeGlobals.map((fee) => (
                <li
                  key={fee.fee_key}
                  className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm"
                >
                  <div>
                    <p className="font-medium text-heading">{fee.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {fee.fee_key} · {fee.payer}
                    </p>
                  </div>
                  <Badge>{formatFeeRate(fee)}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {showCreate && canManage ? (
          <Card className="p-5">
            <SectionHeader title="Add override for this host" />
            <div className="mt-4">
              <HostFeeOverrideForm
                value={form}
                onChange={setForm}
                onSubmit={() => void onCreate()}
                busy={busy}
                lockHostId
                submitLabel="Create override"
              />
            </div>
          </Card>
        ) : null}

        {overrides == null ? (
          <SkeletonLoader lines={4} />
        ) : overrides.length === 0 ? (
          <EmptyState
            title="No overrides for this host"
            description="This host currently uses global fee settings."
          />
        ) : (
          <Card className="overflow-hidden p-0">
            <div className="border-b border-border px-4 py-3">
              <SectionHeader title="Host overrides" />
            </div>
            <DataTable
              columns={[
                {
                  key: "fee",
                  header: "Fee",
                  cell: (row) => (
                    <div>
                      <p className="font-medium">{row.fee_key}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatFeeRate(row)}
                      </p>
                    </div>
                  ),
                },
                {
                  key: "payer",
                  header: "Payer",
                  cell: (row) => row.payer,
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (row) => (
                    <StatusBadge
                      status={row.enabled ? "active" : "inactive"}
                      label={row.enabled ? "Enabled" : "Disabled"}
                    />
                  ),
                },
                {
                  key: "effective",
                  header: "Effective",
                  cell: (row) => formatDateTime(row.effective_from),
                },
                {
                  key: "reason",
                  header: "Reason",
                  cell: (row) => row.reason || "—",
                },
                {
                  key: "actions",
                  header: "",
                  cell: (row) =>
                    canManage && row.enabled ? (
                      <ConfirmAction
                        label="Disable"
                        title="Disable override?"
                        description="Host will fall back to global fees."
                        confirmLabel="Disable"
                        busy={busy}
                        onConfirm={() => void disableOverride(row.id)}
                      />
                    ) : null,
                },
              ]}
              rows={overrides}
              rowKey={(row) => row.id}
            />
          </Card>
        )}

        <FeePreviewCalculator
          settings={settings}
          overrides={overrides ?? []}
          defaultHostId={hostId}
          hosts={[
            {
              id: hostId,
              label: hostName ?? `Host ${hostId.slice(0, 8)}…`,
            },
          ]}
        />
      </div>
    </DashboardShell>
  );
}
