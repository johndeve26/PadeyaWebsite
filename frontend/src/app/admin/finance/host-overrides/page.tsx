"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminFinanceSubnav } from "@/components/admin/AdminFinanceSubnav";
import {
  HostFeeOverrideForm,
  emptyOverrideForm,
  type OverrideFormState,
} from "@/components/admin/HostFeeOverrideForm";
import { datetimeLocalToIso, fixedMajorToMinor } from "@/components/admin/FeeSettingForm";
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
  FilterBar,
  Input,
  SectionHeader,
  SkeletonLoader,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { formatDateTime } from "@/lib/format";
import { formatFeeRate } from "@/lib/fee-preview";
import {
  createHostFeeOverride,
  fetchHostFeeOverrides,
  updateHostFeeOverride,
} from "@/lib/fees-api";
import type { HostFeeOverride } from "@/lib/types/fees";

export default function AdminHostOverridesPage() {
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

  const [rows, setRows] = useState<HostFeeOverride[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hostFilter, setHostFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<OverrideFormState>(emptyOverrideForm);
  const [busy, setBusy] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<OverrideFormState | null>(null);

  const load = useCallback(async () => {
    const data = await fetchHostFeeOverrides({ include_disabled: true });
    setRows(data);
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
            err instanceof ApiError
              ? err.detail
              : "Failed to load host fee overrides",
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
    const list = rows ?? [];
    const q = hostFilter.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (r) =>
        r.host_id.toLowerCase().includes(q) ||
        r.fee_key.toLowerCase().includes(q),
    );
  }, [rows, hostFilter]);

  async function onCreate() {
    setBusy(true);
    setError(null);
    try {
      await createHostFeeOverride({
        host_id: form.host_id.trim(),
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
      toast.push({ tone: "success", title: "Host override created" });
      setShowCreate(false);
      setForm(emptyOverrideForm());
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to create override",
      );
    } finally {
      setBusy(false);
    }
  }

  function startEdit(row: HostFeeOverride) {
    const local = emptyOverrideForm(row.host_id);
    const from = new Date(row.effective_from);
    from.setMinutes(from.getMinutes() - from.getTimezoneOffset());
    local.fee_key = row.fee_key;
    local.percentage_value =
      row.percentage_value == null ? "" : String(row.percentage_value);
    local.fixed_value_major =
      row.fixed_value == null ? "" : String(row.fixed_value / 100);
    local.payer = row.payer;
    local.enabled = row.enabled;
    local.effective_from = from.toISOString().slice(0, 16);
    if (row.effective_to) {
      const to = new Date(row.effective_to);
      to.setMinutes(to.getMinutes() - to.getTimezoneOffset());
      local.effective_to = to.toISOString().slice(0, 16);
    }
    local.reason = row.reason ?? "";
    setEditId(row.id);
    setEditForm(local);
  }

  async function onSaveEdit() {
    if (!editId || !editForm) return;
    setBusy(true);
    setError(null);
    try {
      await updateHostFeeOverride(editId, {
        percentage_value: editForm.percentage_value.trim() || null,
        fixed_value: fixedMajorToMinor(editForm.fixed_value_major),
        payer: editForm.payer,
        enabled: editForm.enabled,
        effective_from: datetimeLocalToIso(editForm.effective_from),
        effective_to: editForm.effective_to
          ? datetimeLocalToIso(editForm.effective_to)
          : null,
        reason: editForm.reason.trim() || null,
      });
      toast.push({ tone: "success", title: "Override updated" });
      setEditId(null);
      setEditForm(null);
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to update override",
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
      <DashboardShell tone="soft" eyebrow="Admin" title="Host fee overrides">
        <Alert tone="warning">
          Missing permission <code>admin.finance.view_fees</code>.
        </Alert>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Host fee overrides"
      description="Host-specific rates beat global fees when enabled and in their effective window."
      actions={
        canManage ? (
          <Button onClick={() => setShowCreate((v) => !v)}>
            {showCreate ? "Close form" : "Add override"}
          </Button>
        ) : null
      }
    >
      <div className="space-y-6">
        <AdminFinanceSubnav />
        {!canManage ? (
          <Alert tone="info">
            View-only. Need <code>admin.finance.manage_host_overrides</code> to
            edit.
          </Alert>
        ) : null}
        {error ? <Alert tone="danger">{error}</Alert> : null}

        <Alert tone="info" title="Fee settings can differ by host">
          Host overrides beat matching global fees when enabled and in their
          effective window. Order fee snapshots preserve the fee terms used at
          the time of sale.
        </Alert>

        {showCreate && canManage ? (
          <Card className="p-5">
            <SectionHeader
              title="Add host override"
              description="Example: Host A ticket commission 3% while global is 5%."
            />
            <div className="mt-4">
              <HostFeeOverrideForm
                value={form}
                onChange={setForm}
                onSubmit={() => void onCreate()}
                busy={busy}
                submitLabel="Create override"
              />
            </div>
          </Card>
        ) : null}

        {editForm && editId && canManage ? (
          <Card className="p-5">
            <SectionHeader title="Edit override" />
            <div className="mt-4">
              <HostFeeOverrideForm
                value={editForm}
                onChange={setEditForm}
                onSubmit={() => void onSaveEdit()}
                busy={busy}
                lockHostId
                submitLabel="Save override"
              />
            </div>
            <Button
              className="mt-3"
              variant="ghost"
              onClick={() => {
                setEditId(null);
                setEditForm(null);
              }}
            >
              Cancel
            </Button>
          </Card>
        ) : null}

        <FilterBar>
          <Input
            label="Filter by host ID or fee key"
            value={hostFilter}
            onChange={(e) => setHostFilter(e.target.value)}
          />
        </FilterBar>

        {rows == null ? (
          <SkeletonLoader lines={5} />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No host overrides"
            description="Add an override when a host needs a custom commission or service fee."
          />
        ) : (
          <Card className="overflow-hidden p-0">
            <DataTable
              columns={[
                {
                  key: "host",
                  header: "Host",
                  cell: (row) => (
                    <div>
                      <Link
                        href={`/admin/hosts/${row.host_id}/fees`}
                        className="font-medium text-heading underline-offset-2 hover:underline"
                      >
                        {row.host_id.slice(0, 8)}…
                      </Link>
                      <p className="text-xs text-muted-foreground">
                        Open host fees
                      </p>
                    </div>
                  ),
                },
                {
                  key: "fee_key",
                  header: "Fee",
                  cell: (row) => (
                    <div>
                      <Badge>{row.fee_key}</Badge>
                      <p className="mt-1 text-xs text-muted-foreground">
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
                    canManage ? (
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => startEdit(row)}
                        >
                          Edit
                        </Button>
                        {row.enabled ? (
                          <ConfirmAction
                            label="Disable"
                            title="Disable override?"
                            description="Host will fall back to global fee settings."
                            confirmLabel="Disable"
                            busy={busy}
                            onConfirm={() => void disableOverride(row.id)}
                          />
                        ) : null}
                      </div>
                    ) : null,
                },
              ]}
              rows={filtered}
              rowKey={(row) => row.id}
            />
          </Card>
        )}
      </div>
    </DashboardShell>
  );
}
