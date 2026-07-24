"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { RequireHostOwner } from "@/components/hosts/RequireHostOwner";
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
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  archiveHostBankAccount,
  createHostBankAccount,
  fetchHostBankAccounts,
  restoreHostBankAccount,
} from "@/lib/hosts-lifecycle-api";
import type { HostBankAccount } from "@/lib/types/lifecycle";

export default function HostBankAccountsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<HostBankAccount[]>([]);
  const [search, setSearch] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [label, setLabel] = useState("");
  const [bankName, setBankName] = useState("");
  const [accountName, setAccountName] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [currency, setCurrency] = useState("NGN");
  const [isDefault, setIsDefault] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load(include = includeArchived) {
    setRows(await fetchHostBankAccounts(include));
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchHostBankAccounts(includeArchived);
        if (active) setRows(items);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load accounts");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [includeArchived]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) => {
      const haystack = [
        row.label,
        row.bank_name,
        row.account_name,
        row.account_number_last4,
        row.currency,
        row.status,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [rows, search]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await createHostBankAccount({
        label: label.trim(),
        bank_name: bankName.trim(),
        account_name: accountName.trim(),
        account_number: accountNumber.trim(),
        currency: currency.trim() || "NGN",
        is_default: isDefault,
      });
      setLabel("");
      setBankName("");
      setAccountName("");
      setAccountNumber("");
      setIsDefault(false);
      toast.push({ title: "Bank account added", tone: "success" });
      await load();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Create failed";
      setError(detail);
      toast.push({ title: "Could not add account", description: detail, tone: "danger" });
    }
  }

  async function onArchive(id: string) {
    setBusyId(id);
    setError(null);
    try {
      await archiveHostBankAccount(id);
      toast.push({ title: "Account archived", tone: "success" });
      await load();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Archive failed";
      setError(detail);
      toast.push({ title: "Archive failed", description: detail, tone: "danger" });
    } finally {
      setBusyId(null);
    }
  }

  async function onRestore(id: string) {
    setBusyId(id);
    setError(null);
    try {
      await restoreHostBankAccount(id);
      toast.push({ title: "Account restored", tone: "success" });
      await load();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Restore failed";
      setError(detail);
      toast.push({ title: "Restore failed", description: detail, tone: "danger" });
    } finally {
      setBusyId(null);
    }
  }

  function renderActions(row: HostBankAccount) {
    const busy = busyId === row.id;
    const archived = row.archived_at != null;
    return (
      <div className="flex flex-wrap justify-end gap-1.5 md:justify-start">
        <Link href={`/host/bank-accounts/${row.id}`}>
          <Button size="sm" variant="secondary">
            View
          </Button>
        </Link>
        {archived ? (
          <ConfirmAction
            label="Restore"
            title="Restore bank account?"
            description={`Restore “${row.label}”. It can be selected for new payouts again.`}
            confirmLabel="Restore account"
            disabled={busy}
            busy={busy}
            onConfirm={() => onRestore(row.id)}
          />
        ) : (
          <ConfirmAction
            label="Archive"
            title="Archive bank account?"
            description={`Archive “${row.label}”. It cannot be used for new payouts until restored.`}
            confirmLabel="Archive account"
            tone="danger"
            disabled={busy}
            busy={busy}
            onConfirm={() => onArchive(row.id)}
          />
        )}
      </div>
    );
  }

  return (
    <RequireHostOwner>
      <DashboardShell
        tone="soft"
        eyebrow="Payouts"
        title="Bank accounts"
        description="Payout destinations for your host account. Full account numbers are never shown after creation."
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        <Card className="mb-8 max-w-2xl space-y-4">
          <SectionHeader
            title="Add bank account"
            description="Enter payout details once. For security, the full account number is encrypted and never displayed again — only the last four digits are shown."
          />
          <form className="space-y-4" onSubmit={onCreate}>
            <Input
              label="Label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Primary NGN account"
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
              label="Account number"
              value={accountNumber}
              onChange={(e) => setAccountNumber(e.target.value)}
              inputMode="numeric"
              hint="Stored encrypted. You will only see ••••last4 after saving."
              required
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Currency"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                placeholder="NGN"
              />
              <label className="flex cursor-pointer items-center gap-2 self-end pb-2 text-sm text-foreground">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-[var(--brand-green)]"
                  checked={isDefault}
                  onChange={(e) => setIsDefault(e.target.checked)}
                />
                <span className="font-semibold">Set as default payout account</span>
              </label>
            </div>
            <Button type="submit">Add account</Button>
          </form>
        </Card>

        <div className="space-y-4">
          <SectionHeader
            title="Your accounts"
            description={`${filtered.length} account${filtered.length === 1 ? "" : "s"}${includeArchived ? " (including archived)" : ""}.`}
          />

          {!loading && rows.length > 0 ? (
            <FilterBar
              trailing={
                <label className="flex cursor-pointer items-center gap-2 text-sm text-foreground">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-[var(--brand-green)]"
                    checked={includeArchived}
                    onChange={(e) => setIncludeArchived(e.target.checked)}
                  />
                  <span className="font-semibold">Show archived</span>
                </label>
              }
            >
              <Input
                label="Search"
                placeholder="Label, bank, status…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </FilterBar>
          ) : null}

          {loading ? null : rows.length === 0 ? (
            <EmptyState
              title="No bank accounts yet"
              description="Add a payout destination to receive host earnings."
            />
          ) : (
            <DataTable
              rows={filtered}
              rowKey={(row) => row.id}
              emptyTitle="No matching accounts"
              emptyDescription="Try a different search term."
              columns={[
                {
                  key: "label",
                  header: "Account",
                  primary: true,
                  cell: (row) => (
                    <div className="space-y-0.5">
                      <p className="font-semibold text-foreground">{row.label}</p>
                      <p className="text-sm text-muted-foreground">{row.account_name}</p>
                    </div>
                  ),
                },
                {
                  key: "bank",
                  header: "Bank",
                  cell: (row) => row.bank_name,
                },
                {
                  key: "last4",
                  header: "Number",
                  cell: (row) => (
                    <span className="font-mono text-sm">****{row.account_number_last4}</span>
                  ),
                },
                {
                  key: "currency",
                  header: "Currency",
                  cell: (row) => row.currency,
                },
                {
                  key: "default",
                  header: "Default",
                  cell: (row) =>
                    row.is_default ? (
                      <Badge tone="accent">Default</Badge>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    ),
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (row) => (
                    <div className="flex flex-wrap gap-1.5">
                      <StatusBadge status={row.status} />
                      {row.archived_at ? <StatusBadge status="archived" /> : null}
                    </div>
                  ),
                },
                {
                  key: "actions",
                  header: "Actions",
                  cell: (row) => renderActions(row),
                },
              ]}
              mobileCard={(row) => (
                <Card className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-bold text-foreground">{row.label}</h3>
                    {row.is_default ? <Badge tone="accent">Default</Badge> : null}
                    <StatusBadge status={row.status} />
                    {row.archived_at ? <StatusBadge status="archived" /> : null}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {row.bank_name} · ****{row.account_number_last4} · {row.currency}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Updated {formatDateTime(row.updated_at)}
                  </p>
                  {renderActions(row)}
                </Card>
              )}
            />
          )}
        </div>
      </DashboardShell>
    </RequireHostOwner>
  );
}
