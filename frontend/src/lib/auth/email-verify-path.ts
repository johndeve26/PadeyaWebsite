/** Paths for email verification gate after signup/login. */

import { safeNextPath } from "@/lib/auth/safe-next";

function isVerifyPath(path: string): boolean {
  return path === "/verify" || path.startsWith("/verify?");
}

/** `/verify` with optional post-verify destination. */
export function emailVerifyPath(next?: string | null): string {
  const dest = safeNextPath(next, "/dashboard");
  if (isVerifyPath(dest)) return "/verify";
  return `/verify?next=${encodeURIComponent(dest)}`;
}

/**
 * After login/register: unverified users must verify before dashboard/workspaces.
 * Verified users continue to `next` (or caller fallback).
 */
export function postAuthPath(
  user: { is_verified: boolean },
  next?: string | null,
  verifiedFallback = "/dashboard",
): string {
  if (!user.is_verified) {
    return emailVerifyPath(next ?? verifiedFallback);
  }
  return safeNextPath(next, verifiedFallback);
}
