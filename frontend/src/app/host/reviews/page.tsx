"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  SectionHeader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { fetchHostReviews, replyToReview, reportReview } from "@/lib/reviews-api";
import type { VerifiedReview } from "@/lib/types/legacy";

export default function HostReviewsPage() {
  const [reviews, setReviews] = useState<VerifiedReview[]>([]);
  const [replies, setReplies] = useState<Record<string, string>>({});
  const [reportReasons, setReportReasons] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setReviews(await fetchHostReviews());
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchHostReviews();
        if (active) setReviews(items);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load reviews");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onReply(id: string) {
    const body = replies[id]?.trim();
    if (!body) return;
    try {
      await replyToReview(id, body);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Reply failed");
    }
  }

  async function onReport(id: string) {
    const reason = reportReasons[id]?.trim();
    if (!reason) return;
    try {
      await reportReview(id, reason);
      setReportReasons((prev) => ({ ...prev, [id]: "" }));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Report failed");
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Legacy"
        title="Verified reviews"
        description="You can reply or report. You cannot delete, edit, or hide reviews."
      >
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}

        <div>
          <Badge tone="neutral">{reviews.length} reviews</Badge>
        </div>

        <div className="space-y-4">
          {reviews.length === 0 ? (
            <EmptyState
              title="No reviews yet"
              description="Verified reviews from attendees will appear here after your events."
            />
          ) : (
            reviews.map((review) => (
              <Card key={review.id} className="space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-lg font-extrabold text-foreground">
                        {review.rating}/5 · {review.event_title}
                      </p>
                      <Badge tone={review.status === "visible" ? "accent" : "neutral"}>
                        {review.status}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {review.reviewer_name} ·{" "}
                      {formatDateTime(review.created_at)}
                    </p>
                  </div>
                </div>

                {review.title ? (
                  <p className="font-semibold text-foreground">{review.title}</p>
                ) : null}
                <p className="text-sm leading-relaxed whitespace-pre-wrap text-muted-foreground">
                  {review.body}
                </p>

                {review.reply ? (
                  <div className="rounded-[var(--radius-md)] border-l-4 border-accent bg-[color-mix(in_srgb,var(--brand-green)_6%,transparent)] px-4 py-3">
                    <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                      Your reply
                    </p>
                    <p className="mt-1 text-sm whitespace-pre-wrap text-foreground">
                      {review.reply.body}
                    </p>
                  </div>
                ) : null}

                <div className="grid gap-4 border-t border-border pt-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <SectionHeader title="Reply" />
                    <Input
                      label="Your response"
                      value={replies[review.id] ?? review.reply?.body ?? ""}
                      onChange={(e) =>
                        setReplies((prev) => ({ ...prev, [review.id]: e.target.value }))
                      }
                    />
                    <Button size="sm" onClick={() => void onReply(review.id)}>
                      {review.reply ? "Update reply" : "Post reply"}
                    </Button>
                  </div>
                  <div className="space-y-2">
                    <SectionHeader title="Report" />
                    <Input
                      label="Report reason"
                      value={reportReasons[review.id] ?? ""}
                      onChange={(e) =>
                        setReportReasons((prev) => ({
                          ...prev,
                          [review.id]: e.target.value,
                        }))
                      }
                      placeholder="Spam, harassment, etc."
                    />
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => void onReport(review.id)}
                    >
                      Report review
                    </Button>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
