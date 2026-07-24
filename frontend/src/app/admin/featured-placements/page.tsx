"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchFeaturedPlacementContexts,
  updateFeaturedPlacementSetStatus,
  type FeaturedPlacementContext,
} from "@/lib/placements-api";

function statusTone(
  status: string | null | undefined,
): "neutral" | "success" | "warning" | "danger" {
  if (status === "active") return "success";
  if (status === "scheduled") return "warning";
  if (status === "expired" || status === "archived") return "danger";
  return "neutral";
}

export default function AdminFeaturedPlacementsListPage() {
  const [rows, setRows] = useState<FeaturedPlacementContext[] | null>(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchFeaturedPlacementContexts({
      include_archived: includeArchived,
    });
    setRows(data);
  }, [includeArchived]);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        await load();
        if (alive) setError(null);
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load placements",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, [load]);

  async function setStatus(
    row: FeaturedPlacementContext,
    status: "active" | "draft" | "archived",
  ) {
    if (!row.id) return;
    setBusyId(row.id);
    setError(null);
    try {
      await updateFeaturedPlacementSetStatus(row.id, status);
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to update status",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <RequireAuth roles={["super_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Admin"
        title="Featured Placement Slots"
        description="Curate Primary and Secondary Spotlights for each discovery context. Public surfaces show these as Pàdéyá Picks."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/admin/events/picks">
              <Button variant="secondary">Listing Pàdéyá Picks</Button>
            </Link>
            <Link href="/admin/events">
              <Button variant="secondary">All events</Button>
            </Link>
            <Link href="/admin/featured-placements/new">
              <Button>New placement</Button>
            </Link>
          </div>
        }
      >
        {error ? <Alert tone="danger" title={error} /> : null}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
            />
            Show archived
          </label>
        </div>

        {rows === null ? (
          <SkeletonLoader />
        ) : rows.length === 0 ? (
          <EmptyState
            title="No placement sets yet"
            description="Create a Featured Placement set for homepage, events, or a location/category surface."
            action={
              <Link href="/admin/featured-placements/new">
                <Button>New placement</Button>
              </Link>
            }
          />
        ) : (
          <div className="grid gap-3">
            {rows.map((row) => {
              const filled = row.slots.filter((s) => s.event_id).length;
              const setId = row.id;
              return (
                <Card
                  key={row.placement_key || row.context_key}
                  className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                        {row.context_label}
                      </p>
                      <Badge tone={statusTone(row.status)}>
                        {row.status || "draft"}
                      </Badge>
                    </div>
                    <h2 className="truncate text-lg font-extrabold text-foreground">
                      {row.display_title}
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      {filled}/2 spotlights filled
                      {row.slots[0]?.event?.title
                        ? ` · ${row.slots[0].event.title}`
                        : ""}
                      {row.slots[1]?.event?.title
                        ? ` · ${row.slots[1].event.title}`
                        : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {setId ? (
                      <Link href={`/admin/featured-placements/${setId}/edit`}>
                        <Button variant="secondary" size="sm">
                          Edit
                        </Button>
                      </Link>
                    ) : null}
                    {setId && row.status !== "active" ? (
                      <Button
                        size="sm"
                        disabled={busyId === setId}
                        onClick={() => void setStatus(row, "active")}
                      >
                        Activate
                      </Button>
                    ) : null}
                    {setId && row.status === "active" ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busyId === setId}
                        onClick={() => void setStatus(row, "draft")}
                      >
                        Deactivate
                      </Button>
                    ) : null}
                    {setId && row.status !== "archived" ? (
                      <ConfirmAction
                        label="Archive"
                        title="Archive this placement set?"
                        description="Archived sets stop showing on public discovery surfaces."
                        confirmLabel="Archive"
                        tone="danger"
                        variant="secondary"
                        size="sm"
                        disabled={busyId === setId}
                        onConfirm={() => setStatus(row, "archived")}
                      />
                    ) : null}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </DashboardShell>
    </RequireAuth>
  );
}
