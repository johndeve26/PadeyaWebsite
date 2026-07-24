"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  EmptyState,
  FilterBar,
  Select,
  SkeletonLoader,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminMerchReviews,
  moderateMerchReview,
  type MerchReviewPublic,
} from "@/lib/merch-api";

export default function AdminMerchReviewsPage() {
  const [rows, setRows] = useState<MerchReviewPublic[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchAdminMerchReviews({
      status: statusFilter === "all" ? undefined : statusFilter,
      limit: 200,
    });
    setRows(data);
    setNotes((prev) => {
      const next = { ...prev };
      for (const row of data) {
        if (next[row.id] === undefined) {
          next[row.id] = row.admin_note ?? "";
        }
      }
      return next;
    });
  }, [statusFilter]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Could not load reviews",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function onModerate(id: string, action: "hide" | "restore") {
    setBusyId(id);
    setError(null);
    try {
      await moderateMerchReview(id, {
        action,
        note: notes[id]?.trim() || null,
      });
      setNote(action === "hide" ? "Review hidden" : "Review restored");
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not moderate review",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Merch reviews"
      description="Hide or restore verified product reviews. Hosts cannot delete reviews."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/merchandise">
            <Button variant="secondary" size="sm">
              Products
            </Button>
          </Link>
          <Link href="/admin/merchandise/reports">
            <Button variant="secondary" size="sm">
              Reports
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Unavailable">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Updated">
          {note}
        </Alert>
      ) : null}

      <FilterBar>
        <Select
          label="Review status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="all">All visible</option>
          <option value="published">Published</option>
          <option value="pending">Pending</option>
          <option value="hidden_by_admin">Hidden by admin</option>
          <option value="removed_by_user">Removed by user</option>
        </Select>
      </FilterBar>

      {rows === null ? <SkeletonLoader lines={4} /> : null}
      {rows && rows.length === 0 ? (
        <EmptyState
          title="No reviews"
          description="No merch reviews match this filter."
        />
      ) : null}
      {rows && rows.length > 0 ? (
        <ul className="space-y-6">
          {rows.map((r) => (
            <li key={r.id} className="space-y-3 border-b border-border pb-6">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-semibold">{r.product_name || "Product"}</p>
                <StatusBadge status={r.status} />
                <Badge tone="neutral" size="sm">
                  Verified purchase
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                {r.author_display_name} · {"★".repeat(r.rating)}
                {r.event_title ? ` · ${r.event_title}` : ""}
              </p>
              {r.body ? <p className="text-sm">{r.body}</p> : null}
              {r.host_reply ? (
                <p className="text-sm text-muted-foreground">
                  Host reply: {r.host_reply}
                </p>
              ) : null}
              <Textarea
                value={notes[r.id] ?? ""}
                onChange={(e) =>
                  setNotes((prev) => ({ ...prev, [r.id]: e.target.value }))
                }
                placeholder="Admin note (optional)"
                rows={2}
              />
              <div className="flex flex-wrap gap-2">
                {r.status !== "hidden_by_admin" ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busyId === r.id}
                    onClick={() => void onModerate(r.id, "hide")}
                  >
                    Hide
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    disabled={busyId === r.id}
                    onClick={() => void onModerate(r.id, "restore")}
                  >
                    Restore
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </DashboardShell>
  );
}
