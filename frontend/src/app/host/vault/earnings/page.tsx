"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { VaultStudioShell } from "@/components/vault/studio/VaultStudioShell";
import { Alert, Button, MetricCard, SkeletonLoader, StatCard } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import { fetchHostVaultEarnings } from "@/lib/vault-api";
import type { VaultEarnings } from "@/lib/types/vault";

export default function HostVaultEarningsPage() {
  const [earnings, setEarnings] = useState<VaultEarnings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchHostVaultEarnings();
        if (active) setEarnings(data);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load earnings");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <VaultStudioShell
      title="Vault earnings"
      description="Revenue from one-time Vault purchases — exclusive host content fans unlock by purchase (and other access paths)."
      actions={
        <Link href="/host/payouts">
          <Button size="sm" variant="secondary">
            Payouts
          </Button>
        </Link>
      }
    >
      <div className="relative mb-8 overflow-hidden rounded-[var(--radius-xl)] bg-ink px-5 py-6 text-paper sm:px-8">
        <div
          aria-hidden
          className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-80"
        />
        <div className="relative space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">
            Monetization overview
          </p>
          <p className="text-2xl font-extrabold tracking-tight sm:text-3xl">
            {earnings ? formatNgn(earnings.gross_revenue) : "—"}
          </p>
          <p className="max-w-xl text-sm text-subtle-foreground">
            Gross revenue from paid Vault unlocks. Available balance appears in Payouts
            after ledger settlement.
          </p>
        </div>
      </div>

      {error ? (
        <Alert tone="danger" title="Could not load earnings">
          {error}
        </Alert>
      ) : null}

      {!earnings && !error ? <SkeletonLoader lines={4} /> : null}

      {earnings ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Gross revenue"
            value={formatNgn(earnings.gross_revenue)}
            hint="All-time unlock revenue"
          />
          <StatCard
            title="Paid unlocks"
            value={earnings.paid_purchase_count}
            hint="Completed purchases"
          />
          <MetricCard
            label="Views"
            value={earnings.view_count}
            description="Total item views across published drops."
          />
          <MetricCard
            label="Published items"
            value={earnings.published_item_count}
            description="Live drops on your Legacy Page."
          />
        </div>
      ) : null}
    </VaultStudioShell>
  );
}
