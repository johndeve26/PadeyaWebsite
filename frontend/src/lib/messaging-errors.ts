import { ApiError } from "@/lib/api";

/** Exact product copy — keep in sync with backend SELF_MESSAGE_DETAIL. */
export const SELF_MESSAGE_DETAIL = "You can’t message yourself.";

/** Exact product copy — keep in sync with backend SELF_FOLLOW_DETAIL. */
export const SELF_FOLLOW_DETAIL = "You can’t follow yourself.";

/** Exact product copy — keep in sync with backend SELF_REPORT_DETAIL. */
export const SELF_REPORT_DETAIL = "You can’t report yourself.";

/** Exact product copy — keep in sync with backend SELF_BLOCK_DETAIL. */
export const SELF_BLOCK_DETAIL = "You can’t block yourself.";

export function formatSelfMessageError(err: unknown, fallback = "Could not send message"): string {
  if (!(err instanceof ApiError)) return fallback;
  const detail = typeof err.detail === "string" ? err.detail.trim() : "";
  if (!detail) return fallback;
  if (
    detail === SELF_MESSAGE_DETAIL ||
    detail.toLowerCase().includes("message yourself") ||
    detail.toLowerCase() === "invalid pair."
  ) {
    return SELF_MESSAGE_DETAIL;
  }
  return detail;
}

export function formatSelfFollowError(err: unknown, fallback = "Could not follow"): string {
  if (!(err instanceof ApiError)) return fallback;
  const detail = typeof err.detail === "string" ? err.detail.trim() : "";
  if (!detail) return fallback;
  if (
    detail === SELF_FOLLOW_DETAIL ||
    detail.toLowerCase().includes("follow yourself")
  ) {
    return SELF_FOLLOW_DETAIL;
  }
  return detail;
}

export function formatSelfReportError(err: unknown, fallback = "Could not report"): string {
  if (!(err instanceof ApiError)) return fallback;
  const detail = typeof err.detail === "string" ? err.detail.trim() : "";
  if (!detail) return fallback;
  if (
    detail === SELF_REPORT_DETAIL ||
    detail.toLowerCase().includes("report yourself")
  ) {
    return SELF_REPORT_DETAIL;
  }
  return detail;
}

export function formatSelfBlockError(err: unknown, fallback = "Could not block"): string {
  if (!(err instanceof ApiError)) return fallback;
  const detail = typeof err.detail === "string" ? err.detail.trim() : "";
  if (!detail) return fallback;
  if (
    detail === SELF_BLOCK_DETAIL ||
    detail.toLowerCase().includes("block yourself")
  ) {
    return SELF_BLOCK_DETAIL;
  }
  return detail;
}
