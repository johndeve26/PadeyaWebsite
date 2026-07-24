"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AdminFinanceSubnav } from "@/components/admin/AdminFinanceSubnav";
import {
  FeeSettingForm,
  datetimeLocalToIso,
  emptyFeeForm,
  fixedMajorToMinor,
  type FeeFormState,
} from "@/components/admin/FeeSettingForm";
import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { minorToMajor } from "@/lib/fee-preview";
import { fetchFeeSettings, updateFeeSetting } from "@/lib/fees-api";
import type { PlatformFeeSetting } from "@/lib/types/fees";

function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

function settingToForm(row: PlatformFeeSetting): FeeFormState {
  return {
    ...emptyFeeForm(),
    fee_key: row.fee_key,
    label: row.label,
    category: row.category,
    fee_type: row.fee_type,
    percentage_value:
      row.percentage_value == null ? "" : String(row.percentage_value),
    fixed_value_major:
      row.fixed_value == null ? "" : String(minorToMajor(row.fixed_value)),
    currency: row.currency,
    payer: row.payer,
    enabled: row.enabled,
    applies_to: row.applies_to,
    notes: row.notes ?? "",
    effective_from: toLocalInput(row.effective_from),
    effective_to: toLocalInput(row.effective_to),
  };
}

export default function AdminEditFeePage() {
  const params = useParams();
  const feeId = String(params.feeId ?? "");
  const { user } = useAuth();
  const router = useRouter();
  const toast = useToast();
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

  const [row, setRow] = useState<PlatformFeeSetting | null>(null);
  const [form, setForm] = useState<FeeFormState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(async () => {
    const settings = await fetchFeeSettings({ include_disabled: true });
    const found = settings.find((s) => s.id === feeId) ?? null;
    if (!found) {
      setNotFound(true);
      setRow(null);
      setForm(null);
      return;
    }
    setNotFound(false);
    setRow(found);
    setForm(settingToForm(found));
  }, [feeId]);

  useEffect(() => {
    if (!canView || !feeId) return;
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load fee setting",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [canView, feeId, load]);

  async function save(partial?: Partial<FeeFormState>) {
    if (!form || !canManage) return;
    const next = partial ? { ...form, ...partial } : form;
    setBusy(true);
    setError(null);
    try {
      const updated = await updateFeeSetting(feeId, {
        label: next.label.trim(),
        fee_type: next.fee_type,
        percentage_value:
          next.fee_type === "fixed" || !next.percentage_value.trim()
            ? null
            : next.percentage_value,
        fixed_value:
          next.fee_type === "percentage"
            ? null
            : fixedMajorToMinor(next.fixed_value_major),
        currency: next.currency || "NGN",
        payer: next.payer,
        enabled: next.enabled,
        applies_to: next.applies_to || "all",
        notes: next.notes.trim() || null,
        effective_from: datetimeLocalToIso(next.effective_from),
        effective_to: next.effective_to
          ? datetimeLocalToIso(next.effective_to)
          : null,
      });
      setRow(updated);
      setForm(settingToForm(updated));
      toast.push({ tone: "success", title: "Fee updated" });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to update fee");
    } finally {
      setBusy(false);
    }
  }

  if (!canView) {
    return (
      <DashboardShell tone="soft" eyebrow="Admin" title="Fee setting">
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
      title={row?.label ?? "Fee setting"}
      description="Edit current or future fee schedule. Existing order snapshots stay unchanged."
      actions={
        <Button variant="ghost" onClick={() => router.push("/admin/finance/fees")}>
          Back to fees
        </Button>
      }
    >
      <div className="space-y-6">
        <AdminFinanceSubnav />
        {error ? <Alert tone="danger">{error}</Alert> : null}
        {!canManage ? (
          <Alert tone="info">
            View-only. Missing <code>admin.finance.manage_fees</code>.
          </Alert>
        ) : null}
        {notFound ? (
          <Alert tone="warning">Fee setting not found.</Alert>
        ) : form == null ? (
          <SkeletonLoader lines={8} />
        ) : (
          <Card className="space-y-6 p-5">
            <FeeSettingForm
              value={form}
              onChange={setForm}
              onSubmit={() => void save()}
              busy={busy}
              lockFeeKey
              readOnly={!canManage}
              submitLabel="Save changes"
            />
            {canManage && row?.enabled ? (
              <ConfirmAction
                label="Disable fee"
                title="Disable this fee?"
                description="Disabled fees will not apply to new calculations. Order snapshots stay frozen."
                confirmLabel="Disable"
                tone="danger"
                busy={busy}
                onConfirm={() => void save({ enabled: false })}
              />
            ) : null}
            {canManage && row && !row.enabled ? (
              <Button
                disabled={busy}
                onClick={() => void save({ enabled: true })}
              >
                Re-enable fee
              </Button>
            ) : null}
          </Card>
        )}
      </div>
    </DashboardShell>
  );
}
