"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminFinanceSubnav } from "@/components/admin/AdminFinanceSubnav";
import { FeePreviewCalculator } from "@/components/admin/FeePreviewCalculator";
import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  FilterBar,
  PageToolbar,
  SectionHeader,
  Select,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { formatDateTime } from "@/lib/format";
import { formatFeeRate } from "@/lib/fee-preview";
import { fetchFeeSettings, fetchHostFeeOverrides } from "@/lib/fees-api";
import type { HostFeeOverride, PlatformFeeSetting } from "@/lib/types/fees";
import { FEE_CATEGORY_OPTIONS, FEE_HELP_COPY, PAYER_COPY } from "@/lib/types/fees";

export default function AdminFeesPage() {
  const { user } = useAuth();
  const canView = userHasPermission(
    user,
    "admin.finance.view_fees",
    "admin.finance.manage_fees",
    "admin.full_access",
  );
  const canManage = userHasPermission(
    user,
    "admin.finance.manage_fees",
    "admin.full_access",
  );

  const [rows, setRows] = useState<PlatformFeeSetting[] | null>(null);
  const [overrides, setOverrides] = useState<HostFeeOverride[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState("all");
  const [enabledFilter, setEnabledFilter] = useState("all");

  const load = useCallback(async () => {
    const [settings, hostOverrides] = await Promise.all([
      fetchFeeSettings({ include_disabled: true }),
      fetchHostFeeOverrides({ include_disabled: true }),
    ]);
    setRows(settings);
    setOverrides(hostOverrides);
  }, []);

  useEffect(() => {
    if (!canView) return;
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load fee settings",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [canView, load]);

  const filtered = useMemo(() => {
    let list = rows ?? [];
    if (category !== "all") {
      list = list.filter((r) => r.category === category);
    }
    if (enabledFilter === "enabled") {
      list = list.filter((r) => r.enabled);
    } else if (enabledFilter === "disabled") {
      list = list.filter((r) => !r.enabled);
    }
    return list;
  }, [rows, category, enabledFilter]);

  if (!canView) {
    return (
      <DashboardShell tone="soft" eyebrow="Admin" title="Platform fees">
        <Alert tone="warning">
          Missing permission <code>admin.finance.view_fees</code>. Support roles
          cannot view or edit fee schedules.
        </Alert>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Platform fees"
      description="Configure ticket, merch, Vault, service, and processing fees for Pàdéyá."
      actions={
        canManage ? (
          <Link href="/admin/finance/fees/new">
            <Button>Create fee</Button>
          </Link>
        ) : null
      }
    >
      <div className="space-y-6">
        <AdminFinanceSubnav />
        <PageToolbar>
          <Link href="/admin/finance">
            <Button size="sm" variant="ghost">
              Overview
            </Button>
          </Link>
          <Link href="/admin/finance/host-overrides">
            <Button size="sm" variant="ghost">
              Host overrides
            </Button>
          </Link>
          <Link href="/admin/finance/earnings">
            <Button size="sm" variant="ghost">
              Earnings
            </Button>
          </Link>
        </PageToolbar>

        {!canManage ? (
          <Alert tone="info">
            View-only access. You need{" "}
            <code>admin.finance.manage_fees</code> to create or edit fees.
          </Alert>
        ) : null}

        <Card className="space-y-2 p-4 text-sm text-muted-foreground">
          {FEE_HELP_COPY.map((line) => (
            <p key={line}>{line}</p>
          ))}
          <p>{PAYER_COPY.platform}</p>
        </Card>

        {error ? <Alert tone="danger">{error}</Alert> : null}

        <FilterBar>
          <Select
            label="Category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="all">All categories</option>
            {FEE_CATEGORY_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
          <Select
            label="Status"
            value={enabledFilter}
            onChange={(e) => setEnabledFilter(e.target.value)}
          >
            <option value="all">All</option>
            <option value="enabled">Enabled</option>
            <option value="disabled">Disabled</option>
          </Select>
        </FilterBar>

        {rows == null ? (
          <SkeletonLoader lines={6} />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No fee settings"
            description="Create a platform fee to start collecting commissions and service fees."
            action={
              canManage ? (
                <Link href="/admin/finance/fees/new">
                  <Button>Create fee</Button>
                </Link>
              ) : undefined
            }
          />
        ) : (
          <Card className="overflow-hidden p-0">
            <div className="border-b border-border px-4 py-3">
              <SectionHeader title="Fee schedule" description={`${filtered.length} rows`} />
            </div>
            <DataTable
              columns={[
                {
                  key: "label",
                  header: "Fee",
                  cell: (row) => (
                    <div>
                      <p className="font-medium text-heading">{row.label}</p>
                      <p className="text-xs text-muted-foreground">
                        {row.fee_key}
                      </p>
                    </div>
                  ),
                },
                {
                  key: "category",
                  header: "Category",
                  cell: (row) => <Badge>{row.category}</Badge>,
                },
                {
                  key: "rate",
                  header: "Rate",
                  cell: (row) => formatFeeRate(row),
                },
                {
                  key: "payer",
                  header: "Payer",
                  cell: (row) => row.payer,
                },
                {
                  key: "enabled",
                  header: "Status",
                  cell: (row) => (
                    <StatusBadge
                      status={row.enabled ? "active" : "inactive"}
                      label={row.enabled ? "Enabled" : "Disabled"}
                    />
                  ),
                },
                {
                  key: "effective_from",
                  header: "Effective",
                  cell: (row) => formatDateTime(row.effective_from),
                },
                {
                  key: "actions",
                  header: "",
                  cell: (row) => (
                    <Link href={`/admin/finance/fees/${row.id}`}>
                      <Button size="sm" variant="ghost">
                        {canManage ? "Edit" : "View"}
                      </Button>
                    </Link>
                  ),
                },
              ]}
              rows={filtered}
              rowKey={(row) => row.id}
            />
          </Card>
        )}

        <FeePreviewCalculator
          settings={rows ?? []}
          overrides={overrides}
        />
      </div>
    </DashboardShell>
  );
}
