"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminAISummaryPanel } from "@/components/admin/AdminAISummaryPanel";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Card,
  ConfirmAction,
  EmptyState,
  FilterBar,
  Input,
  Select,
  SkeletonLoader,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchReportedReviews, moderateReview } from "@/lib/reviews-api";
import { formatDateTime } from "@/lib/format";
import type { ReviewReport } from "@/lib/types/legacy";

export default function AdminReviewsPage() {
  const [reports, setReports] = useState<ReviewReport[]>([]);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setReports(await fetchReportedReviews());
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchReportedReviews();
        if (active) setReports(items);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load reports");
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
    return reports.filter((report) => {
      const review = report.review;
      if (!review) return false;
      if (statusFilter === "hidden" && review.status !== "hidden") return false;
      if (statusFilter === "visible" && review.status === "hidden") return false;
      if (!q) return true;
      const haystack = [
        review.body,
        review.event_title,
        review.reviewer_name,
        report.reason,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [reports, search, statusFilter]);

  async function onModerate(reviewId: string, action: "hide" | "restore") {
    const reason = reasons[reviewId]?.trim();
    if (!reason) {
      setError("Moderation reason is required");
      return;
    }
    setError(null);
    try {
      await moderateReview(reviewId, action, reason);
      setReasons((prev) => {
        const next = { ...prev };
        delete next[reviewId];
        return next;
      });
      setNote(action === "hide" ? "Review hidden" : "Review restored");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Moderation failed");
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Review moderation"
      description="Hide or restore reported reviews. Every action is audited with a reason."
    >
      {error ? (
        <Alert tone="danger" title="Action failed">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Updated">
          {note}
        </Alert>
      ) : null}

      <AdminAISummaryPanel
        feature="admin.reports.summary"
        title="Reports AI summary"
        generateLabel="Summarize reports"
        links={[
          { href: "/admin/message-reports", label: "Message reports" },
          { href: "/admin/fan-connect/reports", label: "Fan Connect reports" },
        ]}
      />

      {loading && !error ? <SkeletonLoader lines={4} /> : null}

      {!loading && reports.length > 0 ? (
        <FilterBar
          trailing={
            <span className="text-sm text-muted-foreground">
              {filtered.length} of {reports.length} reports
            </span>
          }
        >
          <Input
            label="Search"
            placeholder="Review text, event, reporter reason…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Select
            label="Review visibility"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All reports</option>
            <option value="visible">Visible reviews</option>
            <option value="hidden">Hidden reviews</option>
          </Select>
        </FilterBar>
      ) : null}

      {!loading ? (
      <div className="space-y-4">
        {filtered.map((report) => {
          const review = report.review;
          if (!review) return null;
          const reason = reasons[review.id] ?? "";
          return (
            <Card key={report.id} className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={report.status} label="Report open" />
                <StatusBadge status={review.status} />
                <span className="text-sm text-muted-foreground">
                  Reported {formatDateTime(report.created_at)}
                </span>
              </div>

              <div className="rounded-[var(--radius-md)] border border-border bg-muted px-4 py-3">
                <p className="text-sm font-bold uppercase tracking-[0.08em] text-muted-foreground">
                  Reporter reason
                </p>
                <p className="mt-1 text-sm text-foreground">{report.reason}</p>
              </div>

              <div className="space-y-2">
                <p className="font-bold text-foreground">
                  {review.rating}/5 · {review.event_title}
                </p>
                <p className="text-sm text-muted-foreground">
                  {review.reviewer_name ?? "Anonymous reviewer"}
                </p>
                <p className="text-sm leading-relaxed whitespace-pre-wrap text-foreground">
                  {review.body}
                </p>
              </div>

              <Textarea
                label="Moderation reason"
                hint="Required. Recorded in the audit log."
                value={reason}
                onChange={(e) =>
                  setReasons((prev) => ({ ...prev, [review.id]: e.target.value }))
                }
                className="min-h-[72px]"
                placeholder="Why you are hiding or restoring this review…"
              />

              <div className="flex flex-wrap gap-2">
                <ConfirmAction
                  label="Hide review"
                  title="Hide this review?"
                  description="The review will no longer appear publicly. The host and reviewer are not notified automatically."
                  confirmLabel="Hide review"
                  tone="danger"
                  disabled={!reason.trim()}
                  onConfirm={() => onModerate(review.id, "hide")}
                >
                  {reason.trim() ? (
                    <p className="rounded-[var(--radius-md)] border border-border bg-muted px-3 py-2 text-sm whitespace-pre-wrap">
                      {reason.trim()}
                    </p>
                  ) : (
                    <p className="text-sm text-danger">Add a moderation reason first.</p>
                  )}
                </ConfirmAction>
                <ConfirmAction
                  label="Restore review"
                  title="Restore this review?"
                  description="The review will be visible again on the event and host profile."
                  confirmLabel="Restore review"
                  disabled={!reason.trim()}
                  onConfirm={() => onModerate(review.id, "restore")}
                >
                  {reason.trim() ? (
                    <p className="rounded-[var(--radius-md)] border border-border bg-muted px-3 py-2 text-sm whitespace-pre-wrap">
                      {reason.trim()}
                    </p>
                  ) : (
                    <p className="text-sm text-danger">Add a moderation reason first.</p>
                  )}
                </ConfirmAction>
              </div>
            </Card>
          );
        })}

        {!loading && reports.length === 0 ? (
          <EmptyState
            title="No open review reports"
            description="Reported reviews needing moderation will appear here."
          />
        ) : null}

        {!loading && reports.length > 0 && filtered.length === 0 ? (
          <EmptyState
            title="No matching reports"
            description="Try a different search or visibility filter."
          />
        ) : null}
      </div>
      ) : null}
    </DashboardShell>
  );
}
