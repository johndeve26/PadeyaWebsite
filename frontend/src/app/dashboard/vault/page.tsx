"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { BuyerVaultLibraryCard } from "@/components/vault/buyer/BuyerVaultLibraryCard";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  EmptyState,
  SectionHeader,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { VAULT_DEFINITION } from "@/lib/vault-copy";
import { fetchMyVaultLibrary, fetchMyVaultPurchase } from "@/lib/vault-api";
import type { VaultLibraryItem, VaultLibrarySummary } from "@/lib/types/vault";

function LibrarySection({
  eyebrow,
  title,
  description,
  items,
  emptyTitle,
  emptyDescription,
}: {
  eyebrow: string;
  title: string;
  description: string;
  items: VaultLibraryItem[];
  emptyTitle: string;
  emptyDescription: string;
}) {
  return (
    <section className="space-y-5">
      <SectionHeader eyebrow={eyebrow} title={title} description={description} />
      {items.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <BuyerVaultLibraryCard key={`${eyebrow}-${item.id}`} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}

export default function DashboardVaultPage() {
  const searchParams = useSearchParams();
  const purchaseId = searchParams.get("purchase");
  const [library, setLibrary] = useState<VaultLibrarySummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [pollState, setPollState] = useState<{ purchaseId: string; message: string } | null>(
    null,
  );

  const unlockNote = purchaseId
    ? pollState?.purchaseId === purchaseId
      ? pollState.message
      : "Confirming unlock with Pàdéyá…"
    : null;

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchMyVaultLibrary();
        if (active) setLibrary(data);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load Vault");
        }
      } finally {
        if (active) setLoaded(true);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!purchaseId) return;
    const activePurchaseId = purchaseId;
    let active = true;
    let attempts = 0;

    async function poll() {
      attempts += 1;
      try {
        const purchase = await fetchMyVaultPurchase(activePurchaseId);
        if (!active) return;
        if (purchase.status === "paid") {
          setPollState({
            purchaseId: activePurchaseId,
            message: purchase.item_title
              ? `Unlocked: ${purchase.item_title}`
              : "Vault drop unlocked",
          });
          const data = await fetchMyVaultLibrary();
          if (active) setLibrary(data);
          return;
        }
        if (purchase.status === "failed") {
          setPollState({
            purchaseId: activePurchaseId,
            message: "Payment did not complete. You can try unlocking again.",
          });
          return;
        }
        if (attempts < 12) {
          window.setTimeout(() => {
            void poll();
          }, 1500);
        } else {
          setPollState({
            purchaseId: activePurchaseId,
            message:
              "Still confirming payment. Refresh in a moment — access appears after the webhook.",
          });
        }
      } catch {
        if (active && attempts < 12) {
          window.setTimeout(() => {
            void poll();
          }, 1500);
        } else if (active) {
          setPollState({
            purchaseId: activePurchaseId,
            message: "Unable to confirm unlock yet. Refresh shortly.",
          });
        }
      }
    }

    void poll();
    return () => {
      active = false;
    };
  }, [purchaseId]);

  const stats = library?.stats;
  const isEmpty =
    loaded &&
    library &&
    library.unlocked.length === 0 &&
    library.followed_host_drops.length === 0 &&
    library.ticket_holder_content.length === 0 &&
    library.unlockable.length === 0 &&
    library.purchases.length === 0;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Vault"
      title="My Vault library"
      description={`${VAULT_DEFINITION} Access is always re-checked server-side.`}
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/vault/subscriptions">
            <Button variant="secondary">Subscriptions</Button>
          </Link>
          <Link href="/dashboard/following">
            <Button variant="secondary">Following</Button>
          </Link>
          <Link href="/hosts">
            <Button variant="ghost">Find hosts</Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Could not load Vault">
          {error}
        </Alert>
      ) : null}

      {unlockNote ? (
        <Alert tone="info" title="Unlock status">
          {unlockNote}
        </Alert>
      ) : null}

      {!loaded && !error ? <SkeletonLoader lines={8} /> : null}

      {isEmpty ? (
        <EmptyState
          title="Your Vault library is empty"
          description="Follow hosts, buy tickets, check in, or unlock paid drops — exclusive content collects here as a fan library."
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Link href="/hosts">
                <Button size="lg">Find hosts</Button>
              </Link>
              <Link href="/dashboard/following">
                <Button size="lg" variant="secondary">
                  See who you follow
                </Button>
              </Link>
            </div>
          }
        />
      ) : null}

      {library && !isEmpty ? (
        <div className="space-y-12">
          <section className="relative overflow-hidden rounded-[var(--radius-xl)] bg-ink px-5 py-8 text-paper sm:px-8">
            <div
              aria-hidden
              className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-75"
            />
            <div className="relative grid gap-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
              <div className="space-y-3">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">
                  Fan content library
                </p>
                <h2 className="max-w-xl text-3xl font-extrabold tracking-tight sm:text-4xl">
                  {stats?.unlocked_count ?? 0} unlocked drop
                  {(stats?.unlocked_count ?? 0) === 1 ? "" : "s"}
                </h2>
                <p className="max-w-lg text-sm leading-relaxed text-subtle-foreground sm:text-base">
                  Behind-the-scenes, ticket-holder rewards, VIP galleries, and paid
                  unlocks from the hosts you support — with access reasons you can trust.
                </p>
                <div className="flex flex-wrap gap-2 pt-1">
                  <Badge tone="accent">Purchased</Badge>
                  <Badge tone="dark">Ticket-holder</Badge>
                  <Badge tone="dark">Follower</Badge>
                  <Badge tone="dark">VIP</Badge>
                  <Badge tone="dark">Checked-in</Badge>
                </div>
              </div>
              <Link href="/hosts">
                <Button size="lg">Discover more hosts</Button>
              </Link>
            </div>
          </section>

          {stats ? (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
              <StatCard title="Unlocked" value={stats.unlocked_count} />
              <StatCard title="From followed hosts" value={stats.followed_count} />
              <StatCard title="Ticket-holder" value={stats.ticket_count} />
              <StatCard title="May unlock" value={stats.unlockable_count} />
              <StatCard title="Paid unlocks" value={stats.purchase_count} />
            </div>
          ) : null}

          <LibrarySection
            eyebrow="Library"
            title="Unlocked Vault items"
            description="Drops you can open now — purchased, follower, ticket, VIP, or checked-in access."
            items={library.unlocked}
            emptyTitle="No unlocked items yet"
            emptyDescription="Unlock a drop or earn access via follow, ticket, or check-in."
          />

          <LibrarySection
            eyebrow="Following"
            title="Followed hosts’ Vault drops"
            description="Exclusive content unlocked because you follow the host."
            items={library.followed_host_drops}
            emptyTitle="No follower drops yet"
            emptyDescription="Follow hosts on their Legacy Page to unlock followers-only Vault content."
          />

          <LibrarySection
            eyebrow="Tickets"
            title="Ticket-holder content"
            description="Recaps and exclusives unlocked by your ticket or VIP access."
            items={library.ticket_holder_content}
            emptyTitle="No ticket-holder drops yet"
            emptyDescription="Buy a ticket or check in — related Vault rewards appear here."
          />

          <LibrarySection
            eyebrow="Discover"
            title="Locked items you may unlock"
            description="Relevant drops from hosts you already follow, buy from, or attend."
            items={library.unlockable}
            emptyTitle="Nothing waiting to unlock"
            emptyDescription="When hosts publish new exclusives, unlockable drops show up here."
          />

          <section className="space-y-5">
            <SectionHeader
              eyebrow="Activity"
              title="Recent Vault activity"
              description="Purchases and access grants across your library."
            />
            {library.activity.length === 0 ? (
              <EmptyState
                title="No recent activity"
                description="Unlocks and purchases will show up here."
              />
            ) : (
              <ul className="divide-y divide-border overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card dark:bg-surface-elevated">
                {library.activity.map((row) => (
                  <li key={row.id}>
                    <Link
                      href={row.href || "/dashboard/vault"}
                      className="flex flex-col gap-1 px-4 py-4 transition-colors hover:bg-surface-muted/80 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-5"
                    >
                      <div className="min-w-0 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="truncate font-extrabold text-foreground">
                            {row.title}
                          </p>
                          {row.access_label ? (
                            <Badge tone="accent">{row.access_label}</Badge>
                          ) : null}
                          <Badge tone="neutral">{row.kind}</Badge>
                        </div>
                        {row.detail ? (
                          <p className="text-sm text-muted-foreground">{row.detail}</p>
                        ) : null}
                      </div>
                      <p className="shrink-0 text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                        {formatDateTime(row.at)}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      ) : null}
    </DashboardShell>
  );
}
