"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  AdminPlacementForm,
  formFromSet,
  formToUpsert,
  type PlacementFormState,
} from "@/components/admin/AdminPlacementForm";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, ConfirmAction, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminEvents } from "@/lib/events-api";
import {
  fetchFeaturedPlacementSet,
  updateFeaturedPlacementSetStatus,
  upsertFeaturedPlacementSet,
  type FeaturedPlacementContext,
} from "@/lib/placements-api";
import type { EventItem } from "@/lib/types/events";

export default function AdminFeaturedPlacementEditPage() {
  const params = useParams<{ id: string }>();
  const setId = params.id;
  const router = useRouter();

  const [setRow, setSetRow] = useState<FeaturedPlacementContext | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [statusBusy, setStatusBusy] = useState(false);

  const load = useCallback(async () => {
    const [setData, eventRows] = await Promise.all([
      fetchFeaturedPlacementSet(setId),
      fetchAdminEvents(),
    ]);
    setSetRow(setData);
    setEvents(
      eventRows.filter(
        (row) => row.status === "published" && row.visibility === "listed",
      ),
    );
  }, [setId]);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        await load();
        if (alive) setError(null);
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load placement",
          );
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, [load]);

  async function onSubmit(form: PlacementFormState) {
    setBusy(true);
    setError(null);
    try {
      const saved = await upsertFeaturedPlacementSet(formToUpsert(form));
      setSetRow(saved);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to save placement");
    } finally {
      setBusy(false);
    }
  }

  async function onStatus(status: "active" | "draft" | "archived") {
    setStatusBusy(true);
    setError(null);
    try {
      const saved = await updateFeaturedPlacementSetStatus(setId, status);
      setSetRow(saved);
      if (status === "archived") {
        router.push("/admin/featured-placements");
      }
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to update status",
      );
    } finally {
      setStatusBusy(false);
    }
  }

  return (
    <RequireAuth roles={["super_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Featured Placement Slots"
        title={setRow?.display_title || "Edit placement"}
        description="Update spotlights, schedule, overrides, and activation for this discovery context."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/admin/featured-placements">
              <Button variant="ghost">Back to list</Button>
            </Link>
            {setRow?.status !== "active" ? (
              <Button
                disabled={statusBusy || !setRow}
                onClick={() => void onStatus("active")}
              >
                Activate
              </Button>
            ) : (
              <Button
                variant="secondary"
                disabled={statusBusy}
                onClick={() => void onStatus("draft")}
              >
                Deactivate
              </Button>
            )}
            {setRow?.status !== "archived" ? (
              <ConfirmAction
                label="Archive"
                title="Archive this placement set?"
                description="It will stop appearing on public discovery surfaces."
                confirmLabel="Archive"
                tone="danger"
                variant="secondary"
                disabled={statusBusy}
                onConfirm={() => onStatus("archived")}
              />
            ) : null}
          </div>
        }
      >
        {error ? <Alert tone="danger" title={error} /> : null}
        {!setRow ? (
          <SkeletonLoader />
        ) : (
          <AdminPlacementForm
            key={setRow.id || setRow.placement_key || setRow.context_key}
            mode="edit"
            initial={formFromSet(setRow)}
            events={events}
            busy={busy}
            error={null}
            lockContext
            onSubmit={onSubmit}
            onCancelHref="/admin/featured-placements"
          />
        )}
      </DashboardShell>
    </RequireAuth>
  );
}
