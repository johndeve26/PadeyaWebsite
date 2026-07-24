"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { RequireHostOwner } from "@/components/hosts/RequireHostOwner";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  Input,
  SectionHeader,
  SkeletonLoader,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useUnsavedChanges } from "@/lib/hooks/useUnsavedChanges";
import {
  archiveHostBankAccount,
  fetchHostBankAccount,
  restoreHostBankAccount,
  updateHostBankAccount,
} from "@/lib/hosts-lifecycle-api";
import type { HostBankAccount } from "@/lib/types/lifecycle";

export default function HostBankAccountDetailPage() {
  const params = useParams<{ id: string }>();
  const toast = useToast();
  const [account, setAccount] = useState<HostBankAccount | null>(null);
  const [label, setLabel] = useState("");
  const [bankName, setBankName] = useState("");
  const [accountName, setAccountName] = useState("");
  const [newAccountNumber, setNewAccountNumber] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyLifecycle, setBusyLifecycle] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const row = await fetchHostBankAccount(params.id);
        if (!active) return;
        setAccount(row);
        setLabel(row.label);
        setBankName(row.bank_name);
        setAccountName(row.account_name);
        setIsDefault(row.is_default);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load account");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  const dirty = useMemo(() => {
    if (!account) return false;
    const baseDirty =
      label !== account.label ||
      bankName !== account.bank_name ||
      accountName !== account.account_name ||
      isDefault !== account.is_default;
    return baseDirty || newAccountNumber.trim().length > 0;
  }, [account, label, bankName, accountName, isDefault, newAccountNumber]);

  useUnsavedChanges(dirty);

  async function reload() {
    const row = await fetchHostBankAccount(params.id);
    setAccount(row);
    setLabel(row.label);
    setBankName(row.bank_name);
    setAccountName(row.account_name);
    setIsDefault(row.is_default);
    setNewAccountNumber("");
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!account) return;
    setSaving(true);
    setError(null);
    try {
      const body: {
        label?: string;
        bank_name?: string;
        account_name?: string;
        account_number?: string;
        is_default?: boolean;
      } = {
        label: label.trim(),
        bank_name: bankName.trim(),
        account_name: accountName.trim(),
        is_default: isDefault,
      };
      if (newAccountNumber.trim()) {
        body.account_number = newAccountNumber.trim();
      }
      await updateHostBankAccount(account.id, body);
      toast.push({ title: "Changes saved", tone: "success" });
      await reload();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Save failed";
      setError(detail);
      toast.push({ title: "Save failed", description: detail, tone: "danger" });
    } finally {
      setSaving(false);
    }
  }

  async function onArchive() {
    if (!account) return;
    setBusyLifecycle(true);
    setError(null);
    try {
      await archiveHostBankAccount(account.id);
      toast.push({ title: "Account archived", tone: "success" });
      await reload();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Archive failed";
      setError(detail);
      toast.push({ title: "Archive failed", description: detail, tone: "danger" });
    } finally {
      setBusyLifecycle(false);
    }
  }

  async function onRestore() {
    if (!account) return;
    setBusyLifecycle(true);
    setError(null);
    try {
      await restoreHostBankAccount(account.id);
      toast.push({ title: "Account restored", tone: "success" });
      await reload();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Restore failed";
      setError(detail);
      toast.push({ title: "Restore failed", description: detail, tone: "danger" });
    } finally {
      setBusyLifecycle(false);
    }
  }

  return (
    <RequireHostOwner>
      <DashboardShell
        tone="soft"
        eyebrow="Payouts"
        title={account?.label ?? "Bank account"}
        description="Update payout details. Full account numbers are never displayed."
        actions={
          <Link href="/host/bank-accounts">
            <Button variant="ghost">Back to accounts</Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {loading && !error ? <SkeletonLoader lines={5} /> : null}

        {!loading && account ? (
          <div className="space-y-6">
            <Card className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={account.status} />
                {account.is_default ? <Badge tone="accent">Default</Badge> : null}
                {account.archived_at ? <StatusBadge status="archived" /> : null}
              </div>
              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                    Account number
                  </dt>
                  <dd className="mt-1 font-mono font-semibold text-foreground">
                    ****{account.account_number_last4}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                    Currency
                  </dt>
                  <dd className="mt-1 text-muted-foreground">{account.currency}</dd>
                </div>
                <div>
                  <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                    Added
                  </dt>
                  <dd className="mt-1 text-muted-foreground">{formatDateTime(account.created_at)}</dd>
                </div>
                <div>
                  <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                    Last updated
                  </dt>
                  <dd className="mt-1 text-muted-foreground">{formatDateTime(account.updated_at)}</dd>
                </div>
              </dl>
            </Card>

            <Card className="max-w-2xl space-y-4">
              <SectionHeader
                title="Edit account"
                description="Leave account number blank to keep the current encrypted value."
              />
              <form className="space-y-4" onSubmit={onSave}>
                <Input
                  label="Label"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  required
                />
                <div className="grid gap-4 sm:grid-cols-2">
                  <Input
                    label="Bank name"
                    value={bankName}
                    onChange={(e) => setBankName(e.target.value)}
                    required
                  />
                  <Input
                    label="Account name"
                    value={accountName}
                    onChange={(e) => setAccountName(e.target.value)}
                    required
                  />
                </div>
                <Input
                  label="New account number (optional)"
                  value={newAccountNumber}
                  onChange={(e) => setNewAccountNumber(e.target.value)}
                  inputMode="numeric"
                  hint="Only enter if replacing the stored number. It will not be shown again after save."
                />
                <label className="flex cursor-pointer items-center gap-2 text-sm text-foreground">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-[var(--brand-green)]"
                    checked={isDefault}
                    onChange={(e) => setIsDefault(e.target.checked)}
                  />
                  <span className="font-semibold">Default payout account</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  <Button type="submit" disabled={!dirty || saving}>
                    {saving ? "Saving…" : "Save changes"}
                  </Button>
                  {dirty ? (
                    <span className="self-center text-xs text-muted-foreground">
                      Unsaved changes
                    </span>
                  ) : null}
                </div>
              </form>
            </Card>

            <Card className="max-w-2xl space-y-4">
              <SectionHeader
                title="Lifecycle"
                description={
                  account.archived_at
                    ? "Restore to allow this account for new payouts."
                    : "Archive to stop using this account for new payouts."
                }
              />
              {account.archived_at ? (
                <ConfirmAction
                  label="Restore account"
                  title="Restore bank account?"
                  description={`Restore “${account.label}”. It can be selected for new payouts again.`}
                  confirmLabel="Restore"
                  disabled={busyLifecycle}
                  busy={busyLifecycle}
                  onConfirm={() => onRestore()}
                />
              ) : (
                <ConfirmAction
                  label="Archive account"
                  title="Archive bank account?"
                  description={`Archive “${account.label}”. It cannot be used for new payouts until restored.`}
                  confirmLabel="Archive"
                  tone="danger"
                  disabled={busyLifecycle}
                  busy={busyLifecycle}
                  onConfirm={() => onArchive()}
                />
              )}
            </Card>
          </div>
        ) : null}

        {!loading && !account && !error ? (
          <Alert tone="warning" title="Not found">
            This bank account could not be loaded.
          </Alert>
        ) : null}
      </DashboardShell>
    </RequireHostOwner>
  );
}
