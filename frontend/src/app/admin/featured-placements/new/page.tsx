"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  AdminPlacementForm,
  emptyPlacementForm,
  formToUpsert,
  type PlacementFormState,
} from "@/components/admin/AdminPlacementForm";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminEvents } from "@/lib/events-api";
import { upsertFeaturedPlacementSet } from "@/lib/placements-api";
import type { EventItem } from "@/lib/types/events";

export default function AdminFeaturedPlacementNewPage() {
  const router = useRouter();
  const [events, setEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    void fetchAdminEvents()
      .then((rows) => {
        if (!alive) return;
        setEvents(
          rows.filter(
            (row) => row.status === "published" && row.visibility === "listed",
          ),
        );
      })
      .catch((err) => {
        if (alive) {
          setLoadError(
            err instanceof ApiError ? err.detail : "Failed to load events",
          );
        }
      });
    return () => {
      alive = false;
    };
  }, []);

  async function onSubmit(form: PlacementFormState) {
    setBusy(true);
    setError(null);
    try {
      const saved = await upsertFeaturedPlacementSet(formToUpsert(form));
      if (saved.id) {
        router.push(`/admin/featured-placements/${saved.id}/edit`);
      } else {
        router.push("/admin/featured-placements");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to create placement");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireAuth roles={["super_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Featured Placement Slots"
        title="New placement"
        description="Choose a discovery context, assign Primary and Secondary Spotlights, then activate when ready."
        actions={
          <Link href="/admin/featured-placements">
            <Button variant="ghost">Back to list</Button>
          </Link>
        }
      >
        {loadError ? <Alert tone="danger" title={loadError} /> : null}
        <AdminPlacementForm
          mode="create"
          initial={emptyPlacementForm()}
          events={events}
          busy={busy}
          error={error}
          onSubmit={onSubmit}
          onCancelHref="/admin/featured-placements"
        />
      </DashboardShell>
    </RequireAuth>
  );
}
