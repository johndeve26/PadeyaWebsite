"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchHostMerchReviews,
  replyToMerchReview,
  type MerchReviewPublic,
} from "@/lib/merch-api";

export default function HostMerchReviewsPage() {
  const [rows, setRows] = useState<MerchReviewPublic[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [replies, setReplies] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchHostMerchReviews();
    setRows(data);
    setReplies((prev) => {
      const next = { ...prev };
      for (const row of data) {
        if (next[row.id] === undefined) {
          next[row.id] = row.host_reply ?? "";
        }
      }
      return next;
    });
  }, []);

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

  async function onReply(id: string) {
    const reply = (replies[id] || "").trim();
    if (reply.length < 2) {
      setError("Reply must be at least 2 characters");
      return;
    }
    setBusyId(id);
    setError(null);
    try {
      await replyToMerchReview(id, reply);
      setNote("Reply saved");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save reply");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title="Product reviews"
        description="Reply to verified merch reviews. Hosts cannot delete reviews on Pàdéyá."
        actions={
          <Link href="/host/merchandise">
            <Button size="sm" variant="secondary">
              All merch
            </Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Unavailable">
            {error}
          </Alert>
        ) : null}
        {note ? (
          <Alert tone="success" title="Saved">
            {note}
          </Alert>
        ) : null}
        {rows === null ? <SkeletonLoader lines={4} /> : null}
        {rows && rows.length === 0 ? (
          <EmptyState
            title="No reviews yet"
            description="Verified buyer reviews for your merch will show up here."
          />
        ) : null}
        {rows && rows.length > 0 ? (
          <ul className="space-y-6">
            {rows.map((r) => (
              <li key={r.id} className="space-y-3 border-b border-border pb-6">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-foreground">
                    {r.product_name || "Product"}
                  </p>
                  <Badge tone="neutral" size="sm">
                    Verified purchase
                  </Badge>
                  {r.status === "hidden_by_admin" ? (
                    <Badge tone="dark" size="sm">
                      Hidden by admin
                    </Badge>
                  ) : null}
                </div>
                <p className="text-sm text-muted-foreground">
                  {r.author_display_name} · {"★".repeat(r.rating)}
                  {r.event_title ? ` · ${r.event_title}` : ""}
                </p>
                {r.body ? (
                  <p className="text-sm text-foreground">{r.body}</p>
                ) : null}
                <label className="block text-xs text-muted-foreground">
                  Your reply
                  <textarea
                    className="mt-1 w-full border border-border bg-background px-3 py-2 text-sm text-foreground"
                    rows={3}
                    value={replies[r.id] ?? ""}
                    onChange={(e) =>
                      setReplies((prev) => ({
                        ...prev,
                        [r.id]: e.target.value,
                      }))
                    }
                  />
                </label>
                <Button
                  size="sm"
                  disabled={busyId === r.id}
                  onClick={() => void onReply(r.id)}
                >
                  {r.host_reply ? "Update reply" : "Reply"}
                </Button>
              </li>
            ))}
          </ul>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
