"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { RequireHostOwner } from "@/components/hosts/RequireHostOwner";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Input,
  MetricCard,
  PayoutCard,
  SectionHeader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import {
  createHostPayout,
  fetchHostBalance,
  fetchHostLedger,
  fetchHostPayouts,
} from "@/lib/finance-api";
import type { HostBalance, LedgerEntry, PayoutRequest } from "@/lib/types/finance";


export default function HostPayoutsPage() {
  const [balance, setBalance] = useState<HostBalance | null>(null);
  const [payouts, setPayouts] = useState<PayoutRequest[]>([]);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [amount, setAmount] = useState("");
  const [bankName, setBankName] = useState("");
  const [accountName, setAccountName] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [b, p, l] = await Promise.all([
      fetchHostBalance(),
      fetchHostPayouts(),
      fetchHostLedger(),
    ]);
    setBalance(b);
    setPayouts(p);
    setLedger(l);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load payouts");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await createHostPayout({
        amount: Number(amount),
        bank: {
          bank_name: bankName,
          account_name: accountName,
          account_number: accountNumber,
        },
        note: note || undefined,
      });
      setAmount("");
      setNote("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Payout request failed");
    }
  }

  return (
    <RequireHostOwner>
      <DashboardShell
        tone="soft"
        eyebrow="Finance"
        title="Payouts"
        description="Request manual payouts from your available balance. Completion is admin-only with evidence."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/host/earnings">
              <Button variant="secondary">Earnings</Button>
            </Link>
            <Link href="/host">
              <Button variant="secondary">Host console</Button>
            </Link>
          </div>
        }
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {balance ? (
          <>
            <div className="relative mb-8 overflow-hidden rounded-[var(--radius-xl)] bg-ink px-5 py-6 text-paper sm:px-8">
              <div
                aria-hidden
                className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-80"
              />
              <div className="relative space-y-2">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary">
                  Available balance
                </p>
                <p className="text-2xl font-extrabold tracking-tight sm:text-3xl">
                  {formatNgn(balance.available_balance)}
                </p>
                <p className="max-w-xl text-sm text-paper/75">
                  Request a payout when you are ready. Admin completes transfers with
                  immutable evidence.
                </p>
              </div>
            </div>

            <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                title="Available"
                value={formatNgn(balance.available_balance)}
                hint="Ready to withdraw"
              />
              <StatCard
                title="Pending payout"
                value={formatNgn(balance.pending_payout_balance)}
                hint="Awaiting admin completion"
              />
              <MetricCard
                label="Lifetime earned"
                value={formatNgn(balance.lifetime_earned)}
                description="Total credited to your host balance."
              />
              <MetricCard
                label="Paid out"
                value={formatNgn(balance.lifetime_paid_out)}
                description="Completed payout transfers."
              />
            </div>
          </>
        ) : null}

        <Card className="mb-8 max-w-xl space-y-4">
          <SectionHeader
            title="Request payout"
            description="Enter bank details exactly as they appear on your account."
          />
          <form className="space-y-4" onSubmit={onSubmit}>
            <Input
              label="Amount (NGN)"
              type="number"
              min="1"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              hint={
                balance
                  ? `Available: ${formatNgn(balance.available_balance)}`
                  : undefined
              }
              required
            />
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
            <Input
              label="Account number"
              value={accountNumber}
              onChange={(e) => setAccountNumber(e.target.value)}
              required
            />
            <Input
              label="Note (optional)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              hint="Internal reference for your records."
            />
            <Button type="submit">Submit payout request</Button>
          </form>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="space-y-4">
            <SectionHeader title="Payout history" />
            {payouts.length === 0 ? (
              <EmptyState
                title="No payout requests yet"
                description="Submit a request when you have available balance."
              />
            ) : (
              <div className="space-y-3">
                {payouts.map((p) => (
                  <PayoutCard key={p.id} payout={p} />
                ))}
              </div>
            )}
          </Card>
          <Card className="space-y-4">
            <SectionHeader
              title="Recent ledger"
              description="Append-only record of earnings and adjustments."
            />
            {ledger.length === 0 ? (
              <EmptyState
                title="No ledger entries yet"
                description="Earnings and adjustments will appear here."
              />
            ) : (
              <ul className="divide-y divide-border text-sm">
                {ledger.slice(0, 12).map((e) => (
                  <li key={e.id} className="flex justify-between gap-3 py-2.5">
                    <span className="capitalize text-muted-foreground">
                      {e.entry_type.replace(/_/g, " ")} · {e.direction}
                    </span>
                    <span className="font-bold text-foreground">{formatNgn(e.amount)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </DashboardShell>
    </RequireHostOwner>
  );
}
