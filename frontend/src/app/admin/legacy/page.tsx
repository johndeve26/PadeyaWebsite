"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
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
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminHostTiers,
  fetchHostTierHistory,
  recalculateAllHostTiers,
  recalculateHostTier,
} from "@/lib/legacy-api";
import { formatDate, formatDateTime } from "@/lib/format";
import type { HostTierSummary, ScoreHistory } from "@/lib/types/legacy";

export default function AdminLegacyPage() {
  const [hosts, setHosts] = useState<HostTierSummary[]>([]);
  const [history, setHistory] = useState<ScoreHistory[]>([]);
  const [selectedHost, setSelectedHost] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setHosts(await fetchAdminHostTiers());
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchAdminHostTiers();
        if (active) setHosts(items);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load host tiers");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return hosts;
    return hosts.filter((host) => {
      const haystack = [
        host.display_name,
        host.username,
        host.tier?.name,
        host.legacy_status,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [hosts, search]);

  async function onRecalcOne(hostId: string) {
    setError(null);
    try {
      await recalculateHostTier(hostId);
      setNote("Host tier recalculated");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Recalculate failed");
    }
  }

  async function onRecalcAll() {
    setError(null);
    try {
      const result = await recalculateAllHostTiers();
      setNote(`Recalculated ${result.recalculated} hosts`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Recalculate all failed");
    }
  }

  async function onHistory(hostId: string) {
    setError(null);
    try {
      setSelectedHost(hostId);
      setHistory(await fetchHostTierHistory(hostId));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "History failed");
    }
  }

  const selectedHostRow = hosts.find((h) => h.host_id === selectedHost);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Legacy tiers"
      description="View host tiers, recalculate scores, and inspect tier history."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/legacy/tiers">
            <Button variant="secondary">Edit tier thresholds</Button>
          </Link>
          <ConfirmAction
            label="Recalculate all hosts"
            title="Recalculate all host tiers?"
            description="Recomputes composite scores for every active host. Use after changing tier thresholds."
            confirmLabel="Recalculate all"
            tone="danger"
            size="md"
            onConfirm={onRecalcAll}
          />
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Action failed">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Done">
          {note}
        </Alert>
      ) : null}

      {loading && !error ? <SkeletonLoader lines={5} /> : null}

      {!loading && hosts.length > 0 ? (
        <FilterBar
          trailing={
            <span className="text-sm text-muted-foreground">
              {filtered.length} of {hosts.length} hosts
            </span>
          }
        >
          <Input
            label="Search hosts"
            placeholder="Name, username, tier…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </FilterBar>
      ) : null}

      {!loading && hosts.length === 0 ? (
        <EmptyState
          title="No active hosts yet"
          description="Host tier summaries appear here once hosts are active on Pàdéyá."
        />
      ) : !loading ? (
        <DataTable
          rows={filtered}
          rowKey={(host) => host.host_id}
          emptyTitle="No matching hosts"
          emptyDescription="Try a different search term."
          columns={[
            {
              key: "host",
              header: "Host",
              primary: true,
              cell: (host) => (
                <div className="space-y-0.5">
                  <p className="font-semibold text-foreground">{host.display_name}</p>
                  <p className="text-sm text-muted-foreground">@{host.username}</p>
                </div>
              ),
            },
            {
              key: "score",
              header: "Score",
              cell: (host) => (
                <span className="font-semibold">
                  {Number(host.composite_score).toFixed(1)}
                </span>
              ),
            },
            {
              key: "tier",
              header: "Tier",
              cell: (host) => (
                <StatusBadge
                  status={host.tier?.slug ?? host.legacy_status}
                  label={host.tier?.name ?? host.legacy_status}
                />
              ),
            },
            {
              key: "updated",
              header: "Updated",
              cell: (host) => formatDate(host.updated_at),
            },
            {
              key: "actions",
              header: "Actions",
              cell: (host) => (
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" onClick={() => void onRecalcOne(host.host_id)}>
                    Recalculate
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => void onHistory(host.host_id)}
                  >
                    History
                  </Button>
                  <Link href={`/@${host.username}`}>
                    <Button size="sm" variant="ghost">
                      Legacy Page
                    </Button>
                  </Link>
                </div>
              ),
            },
          ]}
          mobileCard={(host) => (
            <Card className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-bold text-foreground">{host.display_name}</h3>
                <StatusBadge
                  status={host.tier?.slug ?? host.legacy_status}
                  label={host.tier?.name ?? host.legacy_status}
                />
              </div>
              <p className="text-sm text-muted-foreground">
                @{host.username} · score {Number(host.composite_score).toFixed(1)}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" onClick={() => void onRecalcOne(host.host_id)}>
                  Recalculate
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => void onHistory(host.host_id)}
                >
                  History
                </Button>
                <Link href={`/@${host.username}`}>
                  <Button size="sm" variant="ghost">
                    Legacy Page
                  </Button>
                </Link>
              </div>
            </Card>
          )}
        />
      ) : null}

      {selectedHost ? (
        <Card className="space-y-4">
          <SectionHeader
            eyebrow="Host history"
            title={selectedHostRow?.display_name ?? "Tier history"}
            description={
              selectedHostRow
                ? `@${selectedHostRow.username} · score ${Number(selectedHostRow.composite_score).toFixed(1)}`
                : undefined
            }
            action={
              <Button size="sm" variant="ghost" onClick={() => setSelectedHost(null)}>
                Close
              </Button>
            }
          />
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tier changes recorded for this host.</p>
          ) : (
            <div className="divide-y divide-border">
              {history.map((row) => (
                <div
                  key={row.id}
                  className="flex flex-wrap justify-between gap-3 py-3 text-sm first:pt-0 last:pb-0"
                >
                  <div className="min-w-0 space-y-1">
                    <p className="font-semibold text-foreground">
                      {row.previous_tier_slug ?? "—"} → {row.tier_slug}
                    </p>
                    <p className="text-muted-foreground">{row.reason}</p>
                  </div>
                  <div className="shrink-0 text-right text-muted-foreground">
                    <p className="font-semibold text-foreground">
                      {Number(row.composite_score).toFixed(1)}
                    </p>
                    <p>{formatDateTime(row.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      ) : null}
    </DashboardShell>
  );
}
