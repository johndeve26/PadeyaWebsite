import { apiRequest } from "@/lib/api";
import type {
  ReviewEligibility,
  ReviewReport,
  VerifiedReview,
} from "@/lib/types/legacy";

export async function fetchReviewEligibility(params: {
  ticketId?: string;
  eventId?: string;
}): Promise<ReviewEligibility> {
  const search = new URLSearchParams();
  if (params.ticketId) search.set("ticket_id", params.ticketId);
  if (params.eventId) search.set("event_id", params.eventId);
  return apiRequest<ReviewEligibility>(`/reviews/eligibility?${search.toString()}`);
}

export async function submitReview(input: {
  ticket_id: string;
  rating: number;
  title?: string;
  body: string;
}): Promise<VerifiedReview> {
  return apiRequest<VerifiedReview>("/reviews", { method: "POST", body: input });
}

export async function updateReview(
  reviewId: string,
  input: {
    rating?: number;
    title?: string | null;
    body?: string;
  },
): Promise<VerifiedReview> {
  return apiRequest<VerifiedReview>(`/reviews/${reviewId}`, {
    method: "PATCH",
    body: input,
  });
}

/** Soft withdraw — not a hard delete. Hosts cannot withdraw others' reviews. */
export async function withdrawReview(reviewId: string): Promise<VerifiedReview> {
  return apiRequest<VerifiedReview>(`/reviews/${reviewId}`, {
    method: "DELETE",
  });
}

export async function fetchMyReviews(): Promise<VerifiedReview[]> {
  return apiRequest<VerifiedReview[]>("/reviews/me");
}

export async function fetchHostReviews(): Promise<VerifiedReview[]> {
  return apiRequest<VerifiedReview[]>("/reviews/host/me");
}

export async function replyToReview(
  reviewId: string,
  body: string,
): Promise<VerifiedReview> {
  return apiRequest<VerifiedReview>(`/reviews/${reviewId}/reply`, {
    method: "POST",
    body: { body },
  });
}

export async function reportReview(
  reviewId: string,
  reason: string,
): Promise<ReviewReport> {
  return apiRequest<ReviewReport>(`/reviews/${reviewId}/report`, {
    method: "POST",
    body: { reason },
  });
}

export async function fetchReportedReviews(): Promise<ReviewReport[]> {
  return apiRequest<ReviewReport[]>("/reviews/admin/reported");
}

export async function moderateReview(
  reviewId: string,
  action: "hide" | "restore",
  reason: string,
): Promise<VerifiedReview> {
  return apiRequest<VerifiedReview>(`/reviews/${reviewId}/moderate`, {
    method: "POST",
    body: { action, reason },
  });
}
