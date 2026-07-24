"use client";

import Link from "next/link";

import { SectionLabel } from "@/components/personal/command-center/SectionLabel";
import { Button, Card, SkeletonLoader } from "@/components/ui";
import type { VaultSubscription } from "@/lib/types/lifecycle";
import type { VaultLibrarySummary } from "@/lib/types/vault";

export function VaultSection({
  loading,
  library,
  subscriptions,
}: {
  loading: boolean;
  library: VaultLibrarySummary | null;
  subscriptions: VaultSubscription[] | null;
}) {
  if (loading) {
    return (
      <section className="min-w-0 space-y-3">
        <SectionLabel>Vault</SectionLabel>
        <SkeletonLoader lines={2} />
      </section>
    );
  }

  const unlocked = library?.stats?.unlocked_count ?? 0;
  const titles = (library?.unlocked || [])
    .slice(0, 2)
    .map((item) => item.title)
    .filter(Boolean);
  const activeSubs = (subscriptions || []).filter(
    (s) => (s.status || "").toLowerCase() === "active",
  ).length;

  if (unlocked === 0 && activeSubs === 0) {
    return null;
  }

  return (
    <section className="min-w-0 space-y-3">
      <SectionLabel>Vault</SectionLabel>
      <Card className="min-w-0 space-y-3">
        <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-base font-bold tracking-tight text-foreground sm:text-lg">
              {unlocked > 0
                ? `${unlocked} unlock${unlocked === 1 ? "" : "s"}`
                : "Vault"}
            </h3>
            {titles.length > 0 ? (
              <p className="mt-1 break-words text-sm text-muted-foreground">
                {titles.join(" · ")}
              </p>
            ) : (
              <p className="mt-1 text-sm text-muted-foreground">
                Your unlocked drops stay in your library.
              </p>
            )}
            {activeSubs > 0 ? (
              <p className="mt-1 text-sm text-muted-foreground">
                {activeSubs} active subscription{activeSubs === 1 ? "" : "s"}
              </p>
            ) : null}
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Link href="/dashboard/vault">
              <Button size="sm">Open Vault</Button>
            </Link>
            {activeSubs > 0 ? (
              <Link href="/dashboard/vault/subscriptions">
                <Button size="sm" variant="secondary">
                  Subscriptions
                </Button>
              </Link>
            ) : null}
          </div>
        </div>
      </Card>
    </section>
  );
}
