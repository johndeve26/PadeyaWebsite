"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { VaultDefinitionNote } from "@/components/vault/VaultDefinitionNote";
import { VaultStudioItemCard } from "@/components/vault/studio/VaultStudioItemCard";
import { VaultStudioShell } from "@/components/vault/studio/VaultStudioShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Media,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import { VAULT_HOST_STUDIO_DESCRIPTION } from "@/lib/vault-copy";
import { formatAccessType } from "@/lib/vault-lock-copy";
import {
  archiveHostVaultItem,
  fetchVaultStudio,
  publishHostVaultItem,
  restoreHostVaultItem,
  unpublishHostVaultItem,
} from "@/lib/vault-api";
import type {
  VaultStudioFilter,
  VaultStudioItem,
  VaultStudioSummary,
} from "@/lib/types/vault";
import { cn } from "@/lib/cn";

const FILTERS: { id: VaultStudioFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "draft", label: "Draft" },
  { id: "published", label: "Published" },
  { id: "scheduled", label: "Scheduled" },
  { id: "locked", label: "Locked" },
  { id: "free", label: "Free" },
  { id: "paid", label: "Paid" },
  { id: "ticket-holder", label: "Ticket-holder" },
  { id: "expired", label: "Expired" },
  { id: "archived", label: "Archived" },
  { id: "hidden", label: "Hidden" },
];

function matchesFilter(item: VaultStudioItem, filter: VaultStudioFilter): boolean {
  switch (filter) {
    case "all":
      return true;
    case "draft":
      return item.status === "draft";
    case "published":
      return item.status === "published";
    case "scheduled":
      return item.status === "scheduled" || Boolean(item.is_scheduled);
    case "locked":
      return item.is_access_gated;
    case "free":
      return item.access?.access_type === "free";
    case "paid":
      return item.is_paid;
    case "ticket-holder":
      return item.is_ticket_gated;
    case "expired":
      return item.is_expired || item.status === "expired";
    case "archived":
      return item.is_archived || item.status === "archived";
    case "hidden":
      return item.status === "hidden_by_admin" || Boolean(item.is_hidden_by_admin);
    default:
      return true;
  }
}

export default function HostVaultPage() {
  const [studio, setStudio] = useState<VaultStudioSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<VaultStudioFilter>("all");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionNote, setActionNote] = useState<string | null>(null);

  async function load() {
    const data = await fetchVaultStudio();
    setStudio(data);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load Vault Studio");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const items = useMemo(() => studio?.items ?? [], [studio?.items]);
  const stats = studio?.stats;
  const filtered = useMemo(
    () => items.filter((item) => matchesFilter(item, filter)),
    [items, filter],
  );
  const loading = !studio && !error;

  async function runAction(
    itemId: string,
    action: () => Promise<unknown>,
    note: string,
  ) {
    setBusyId(itemId);
    setError(null);
    setActionNote(null);
    try {
      await action();
      await load();
      setActionNote(note);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <VaultStudioShell
      title="Vault Studio"
      description={VAULT_HOST_STUDIO_DESCRIPTION}
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/host/vault/new">
            <Button size="sm">Quick create</Button>
          </Link>
          <Link href="/host/vault/preview">
            <Button size="sm" variant="secondary">
              Studio preview
            </Button>
          </Link>
          {studio ? (
            <Link href={studio.share_path}>
              <Button size="sm" variant="ghost">
                Public Vault
              </Button>
            </Link>
          ) : null}
        </div>
      }
    >
      <div className="relative mb-8 overflow-hidden rounded-[var(--radius-xl)] bg-ink px-5 py-8 text-paper sm:px-8">
        <div aria-hidden className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-80" />
        <div className="relative grid gap-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <div className="space-y-4">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">
              Vault Studio
            </p>
            <h2 className="max-w-xl text-3xl font-extrabold tracking-tight sm:text-4xl">
              {loading
                ? "Loading studio…"
                : `${stats?.total_items ?? 0} exclusive drop${
                    (stats?.total_items ?? 0) === 1 ? "" : "s"
                  }`}
            </h2>
            <VaultDefinitionNote tone="dark" compact className="max-w-xl" />
          </div>
          <Link href="/host/vault/new">
            <Button size="lg">Create exclusive drop</Button>
          </Link>
        </div>
      </div>

      {error ? (
        <Alert tone="danger" title="Could not load Vault" className="mb-6">
          {error}
        </Alert>
      ) : null}
      {actionNote ? (
        <Alert tone="success" title="Updated" className="mb-6">
          {actionNote}
        </Alert>
      ) : null}

      {studio && stats ? (
        <div className="mb-8 space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Total items" value={stats.total_items} />
            <StatCard title="Published" value={stats.published_items} />
            <StatCard
              title="Locked / gated"
              value={stats.locked_items}
              hint="Require follow, ticket, VIP, invite, or pay"
            />
            <StatCard title="Free items" value={stats.free_items} />
            <StatCard title="Paid unlocks" value={stats.paid_unlocks} />
            <StatCard title="Vault views" value={stats.view_count} />
            <StatCard
              title="Vault earnings"
              value={formatNgn(Number(stats.gross_revenue))}
              href="/host/vault/earnings"
            />
            <Card className="space-y-3">
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                Legacy Vault block
              </p>
              <p className="text-2xl font-extrabold text-foreground">
                {studio.legacy_vault_block_visible ? "Visible" : "Hidden"}
              </p>
              <Link
                href="/host/legacy/content"
                className="text-sm font-semibold text-foreground underline-offset-2 hover:underline"
              >
                Manage blocks
              </Link>
            </Card>
          </div>

          {studio.top_item ? (
            <Card className="overflow-hidden p-0">
              <div className="grid gap-0 sm:grid-cols-[200px_minmax(0,1fr)]">
                <div className="relative aspect-[16/10] bg-surface-dark sm:aspect-auto sm:min-h-[140px]">
                  {studio.top_item.cover_url ? (
                    <Media
                      src={studio.top_item.cover_url}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="padeya-hero-glow absolute inset-0" />
                  )}
                </div>
                <div className="flex flex-col justify-center gap-3 p-5 sm:p-6">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="accent">Top performing</Badge>
                    {studio.top_item.access_type ? (
                      <Badge tone="dark">
                        {formatAccessType(studio.top_item.access_type)}
                      </Badge>
                    ) : null}
                  </div>
                  <div>
                    <h3 className="text-xl font-extrabold text-foreground">
                      {studio.top_item.title}
                    </h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {studio.top_item.view_count} views · {studio.top_item.unlock_count}{" "}
                      unlocks · {formatNgn(Number(studio.top_item.earnings))}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Link href={`/host/vault/${studio.top_item.id}/edit`}>
                      <Button size="sm">Edit</Button>
                    </Link>
                    <Link href={`/host/vault/${studio.top_item.id}/preview`}>
                      <Button size="sm" variant="secondary">
                        Preview
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            </Card>
          ) : null}
        </div>
      ) : null}

      {loading ? <SkeletonLoader lines={8} /> : null}

      {!loading && items.length === 0 && !error ? (
        <div className="space-y-6">
          <EmptyState
            title="No Vault drops yet"
            description="Publish exclusive content fans unlock by following you, buying tickets, attending, VIP access, or a one-time purchase."
            action={
              <Link href="/host/vault/new">
                <Button size="lg">Create first drop</Button>
              </Link>
            }
          />
          <Card className="space-y-3">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
              Example drops
            </p>
            <VaultDefinitionNote showExamples compact />
          </Card>
        </div>
      ) : null}

      {items.length > 0 ? (
        <div className="space-y-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-extrabold text-foreground">Your drops</h2>
              <p className="text-sm text-muted-foreground">
                {filtered.length} shown
                {filter !== "all" ? ` · filter: ${filter}` : ""}
              </p>
            </div>
            <Link href="/host/vault/new">
              <Button size="sm">Quick create</Button>
            </Link>
          </div>

          <div className="flex flex-wrap gap-2">
            {FILTERS.map((row) => {
              const count =
                row.id === "all"
                  ? items.length
                  : items.filter((item) => matchesFilter(item, row.id)).length;
              const active = filter === row.id;
              return (
                <button
                  key={row.id}
                  type="button"
                  onClick={() => setFilter(row.id)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-sm font-semibold transition-colors",
                    active
                      ? "border-ink bg-ink text-paper"
                      : "border-border bg-card text-muted-foreground hover:border-border-strong hover:text-foreground",
                  )}
                >
                  {row.label}
                  <span className="ml-1.5 tabular-nums opacity-70">{count}</span>
                </button>
              );
            })}
          </div>

          {filtered.length === 0 ? (
            <EmptyState
              title="No drops in this filter"
              description="Try another filter or create a new exclusive drop."
              action={
                <Button size="sm" variant="secondary" onClick={() => setFilter("all")}>
                  Show all
                </Button>
              }
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {filtered.map((item) => (
                <VaultStudioItemCard
                  key={item.id}
                  item={item}
                  featured={studio?.featured_vault_item_id === item.id}
                  busy={busyId === item.id}
                  onArchive={() => {
                    if (!confirm("Archive this drop? It leaves the public Vault.")) return;
                    void runAction(
                      item.id,
                      () => archiveHostVaultItem(item.id),
                      "Drop archived",
                    );
                  }}
                  onUnpublish={() => {
                    if (!confirm("Unpublish this drop back to draft?")) return;
                    void runAction(
                      item.id,
                      () => unpublishHostVaultItem(item.id),
                      "Drop unpublished",
                    );
                  }}
                  onPublish={() => {
                    void runAction(
                      item.id,
                      () => publishHostVaultItem(item.id),
                      "Drop published",
                    );
                  }}
                  onRestore={() => {
                    void runAction(
                      item.id,
                      () => restoreHostVaultItem(item.id),
                      "Drop restored as draft",
                    );
                  }}
                />
              ))}
            </div>
          )}
        </div>
      ) : null}
    </VaultStudioShell>
  );
}
