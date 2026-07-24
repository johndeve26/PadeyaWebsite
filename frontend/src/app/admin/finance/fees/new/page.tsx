"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

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
import { Alert, Card, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { createFeeSetting } from "@/lib/fees-api";

export default function AdminCreateFeePage() {
  const { user } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const canManage = userHasPermission(
    user,
    "admin.finance.manage_fees",
    "admin.full_access",
  );
  const [form, setForm] = useState<FeeFormState>(emptyFeeForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit() {
    setBusy(true);
    setError(null);
    try {
      const created = await createFeeSetting({
        fee_key: form.fee_key.trim(),
        label: form.label.trim(),
        category: form.category,
        fee_type: form.fee_type,
        percentage_value:
          form.fee_type === "fixed" || !form.percentage_value.trim()
            ? null
            : form.percentage_value,
        fixed_value:
          form.fee_type === "percentage"
            ? null
            : fixedMajorToMinor(form.fixed_value_major),
        currency: form.currency || "NGN",
        payer: form.payer,
        enabled: form.enabled,
        applies_to: form.applies_to || "all",
        notes: form.notes.trim() || null,
        effective_from: datetimeLocalToIso(form.effective_from),
        effective_to: form.effective_to
          ? datetimeLocalToIso(form.effective_to)
          : null,
      });
      toast.push({ tone: "success", title: "Fee created" });
      router.push(`/admin/finance/fees/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to create fee");
    } finally {
      setBusy(false);
    }
  }

  if (!canManage) {
    return (
      <DashboardShell tone="soft" eyebrow="Admin" title="Create fee">
        <Alert tone="warning">
          Missing permission <code>admin.finance.manage_fees</code>. Unauthorized
          admins cannot create fees.
        </Alert>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Create fee"
      description="Add a platform fee schedule. Changes are audited."
    >
      <div className="space-y-6">
        <AdminFinanceSubnav />
        {error ? <Alert tone="danger">{error}</Alert> : null}
        <Card className="p-5">
          <FeeSettingForm
            value={form}
            onChange={setForm}
            onSubmit={() => void onSubmit()}
            busy={busy}
            submitLabel="Create fee"
          />
        </Card>
      </div>
    </DashboardShell>
  );
}
