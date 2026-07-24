"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";

import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  ReviewCard,
  Select,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { fetchMyTickets } from "@/lib/commerce-api";
import { formatDateTime } from "@/lib/format";
import { ownedHostIds } from "@/lib/host-affiliation";
import {
  fetchMyReviews,
  fetchReviewEligibility,
  submitReview,
  updateReview,
  withdrawReview,
} from "@/lib/reviews-api";
import type { Ticket } from "@/lib/types/commerce";
import type { VerifiedReview } from "@/lib/types/legacy";

export default function DashboardReviewsPage() {
  const searchParams = useSearchParams();
  const prefTicketId = searchParams.get("ticket_id") || "";
  const { workspaces } = useHostWorkspace();
  const affiliatedHostIds = useMemo(
    () => new Set(ownedHostIds(workspaces)),
    [workspaces],
  );
  const [reviews, setReviews] = useState<VerifiedReview[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [ticketId, setTicketId] = useState("");
  const [rating, setRating] = useState(5);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [eligibilityNote, setEligibilityNote] = useState<string | null>(null);
  const [eligible, setEligible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [mine, myTickets] = await Promise.all([
          fetchMyReviews(),
          fetchMyTickets(),
        ]);
        if (!active) return;
        setReviews(mine);
        const checkedIn = myTickets.filter(
          (t) =>
            t.status === "checked_in" &&
            !(t.host_id && affiliatedHostIds.has(t.host_id)),
        );
        setTickets(checkedIn);
        if (
          prefTicketId &&
          checkedIn.some((t) => t.id === prefTicketId)
        ) {
          setTicketId(prefTicketId);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load reviews");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [prefTicketId, affiliatedHostIds]);

  useEffect(() => {
    if (!ticketId || editingId) return;
    let active = true;
    void (async () => {
      try {
        const elig = await fetchReviewEligibility({ ticketId });
        if (!active) return;
        setEligible(Boolean(elig.eligible));
        setEligibilityNote(
          elig.eligible
            ? `Eligible to review${elig.event_title ? `: ${elig.event_title}` : ""}`
            : elig.reason,
        );
      } catch (err) {
        if (active) {
          setEligible(false);
          setEligibilityNote(
            err instanceof ApiError ? err.detail : "Eligibility check failed",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [ticketId, editingId]);

  function resetForm() {
    setEditingId(null);
    setTicketId("");
    setRating(5);
    setTitle("");
    setBody("");
    setEligible(false);
    setEligibilityNote(null);
  }

  function startEdit(review: VerifiedReview) {
    setEditingId(review.id);
    setTicketId(review.ticket_id);
    setRating(review.rating);
    setTitle(review.title || "");
    setBody(review.body);
    setEligible(true);
    setEligibilityNote(
      review.status === "withdrawn"
        ? "Editing will restore this review to public."
        : "Editing your verified review.",
    );
    setError(null);
    setNote(null);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNote(null);
    setBusy(true);
    try {
      if (editingId) {
        const wasWithdrawn =
          reviews.find((r) => r.id === editingId)?.status === "withdrawn";
        const updated = await updateReview(editingId, {
          rating,
          title: title || null,
          body,
        });
        setReviews((prev) =>
          prev.map((r) => (r.id === updated.id ? updated : r)),
        );
        setNote(
          wasWithdrawn && updated.status === "visible"
            ? "Review restored and updated."
            : "Review updated.",
        );
        resetForm();
      } else {
        const created = await submitReview({
          ticket_id: ticketId,
          rating,
          title: title || undefined,
          body,
        });
        setReviews((prev) => [created, ...prev]);
        setNote("Verified review submitted.");
        resetForm();
      }
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : editingId
            ? "Could not update review"
            : "Could not submit review",
      );
    } finally {
      setBusy(false);
    }
  }

  async function onWithdraw(review: VerifiedReview) {
    if (review.status === "withdrawn") return;
    const ok = window.confirm(
      "Withdraw this review? It will no longer appear on the host Legacy Page. You can edit later to restore it.",
    );
    if (!ok) return;
    setError(null);
    setNote(null);
    setBusy(true);
    try {
      const withdrawn = await withdrawReview(review.id);
      setReviews((prev) =>
        prev.map((r) => (r.id === withdrawn.id ? withdrawn : r)),
      );
      if (editingId === review.id) resetForm();
      setNote("Review withdrawn.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not withdraw review");
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      compact
      title="My verified reviews"
      description="Create, edit, or withdraw reviews from events you checked in to. Hosts cannot delete your reviews."
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <Card className="h-fit space-y-5 shadow-[var(--shadow-soft)]">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                {editingId ? "Update" : "Create"}
              </p>
              <h2 className="mt-1 text-xl font-extrabold text-foreground">
                {editingId ? "Edit verified review" : "Write a verified review"}
              </h2>
            </div>
            {editingId ? (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => {
                  resetForm();
                  setNote(null);
                  setError(null);
                }}
              >
                Cancel edit
              </Button>
            ) : null}
          </div>
          <form className="space-y-4" onSubmit={onSubmit}>
            <Select
              label="Checked-in ticket"
              value={ticketId}
              onChange={(e) => {
                setTicketId(e.target.value);
                setEligibilityNote(null);
              }}
              required
              disabled={Boolean(editingId)}
            >
              <option value="">Select ticket</option>
              {tickets.map((ticket) => (
                <option key={ticket.id} value={ticket.id}>
                  {ticket.event_title ?? ticket.public_code} · {ticket.public_code}
                </option>
              ))}
              {editingId &&
              ticketId &&
              !tickets.some((t) => t.id === ticketId) ? (
                <option value={ticketId}>Current review ticket</option>
              ) : null}
            </Select>
            {ticketId && eligibilityNote ? (
              <Alert
                tone={eligible || editingId ? "success" : "warning"}
                title={
                  editingId
                    ? "Editing"
                    : eligible
                      ? "Ready to review"
                      : "Not eligible yet"
                }
              >
                {eligibilityNote}
              </Alert>
            ) : null}

            <div className="space-y-2">
              <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                Rating
              </p>
              <div className="flex flex-wrap gap-2">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    aria-label={`${n} stars`}
                    aria-pressed={rating === n}
                    className={cn(
                      "flex h-11 w-11 items-center justify-center rounded-[var(--radius-md)] border text-lg font-bold transition-colors",
                      rating === n
                        ? "border-accent bg-accent text-primary-foreground"
                        : "border-border bg-surface-elevated text-muted-foreground hover:border-border-strong",
                    )}
                    onClick={() => setRating(n)}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            <Input
              label="Title (optional)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <Textarea
              label="Review"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
              minLength={10}
              hint="At least 10 characters — verified reviews are public on the host Legacy Page"
            />
            {error ? (
              <Alert tone="danger" title="Could not save">
                {error}
              </Alert>
            ) : null}
            {note ? (
              <Alert tone="success" title="Saved">
                {note}
              </Alert>
            ) : null}
            <Button
              type="submit"
              size="lg"
              disabled={busy || !ticketId || (!editingId && !eligible)}
            >
              {busy
                ? "Saving…"
                : editingId
                  ? "Save changes"
                  : "Submit verified review"}
            </Button>
          </form>
        </Card>

        <section className="space-y-4">
          <h2 className="text-xl font-extrabold text-foreground">Your reviews</h2>
          {reviews.length === 0 ? (
            <EmptyState
              title="No reviews yet"
              description="After you check in and the event ends, you can leave a verified review here."
            />
          ) : (
            reviews.map((review) => {
              const withdrawn = review.status === "withdrawn";
              const hidden = review.status === "hidden";
              return (
                <div key={review.id} className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2 px-1">
                    <Badge
                      tone={
                        review.status === "visible"
                          ? "accent"
                          : withdrawn
                            ? "neutral"
                            : "warning"
                      }
                      size="sm"
                    >
                      {review.status}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(review.created_at)}
                    </span>
                  </div>
                  <ReviewCard
                    rating={review.rating}
                    title={review.title}
                    body={review.body}
                    eventTitle={review.event_title}
                    eventHref={
                      review.event_slug ? `/events/${review.event_slug}` : null
                    }
                    reply={review.reply}
                    verified={review.status === "visible"}
                    className={withdrawn || hidden ? "opacity-80" : undefined}
                  />
                  <div className="flex flex-wrap gap-2 px-1">
                    {!hidden ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busy}
                        onClick={() => startEdit(review)}
                      >
                        {withdrawn ? "Edit & restore" : "Edit"}
                      </Button>
                    ) : null}
                    {!withdrawn && !hidden ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy}
                        onClick={() => void onWithdraw(review)}
                      >
                        Withdraw
                      </Button>
                    ) : null}
                  </div>
                </div>
              );
            })
          )}
        </section>
      </div>
    </DashboardShell>
  );
}
