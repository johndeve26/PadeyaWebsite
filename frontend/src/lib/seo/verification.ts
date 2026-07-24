/**
 * Search Console / Bing site verification (Phase 1C).
 * Tokens come from env only — never hardcode.
 */

import type { Metadata } from "next";

export type VerificationEnv = {
  googleSiteVerification?: string | null;
  bingSiteVerification?: string | null;
};

/** Prefer GOOGLE_SITE_VERIFICATION; NEXT_PUBLIC_* also accepted for edge/static emit. */
export function readVerificationEnv(
  env: NodeJS.ProcessEnv = process.env,
): VerificationEnv {
  return {
    googleSiteVerification:
      env.GOOGLE_SITE_VERIFICATION?.trim() ||
      env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION?.trim() ||
      null,
    bingSiteVerification:
      env.BING_SITE_VERIFICATION?.trim() ||
      env.NEXT_PUBLIC_BING_SITE_VERIFICATION?.trim() ||
      null,
  };
}

function cleanToken(raw: string | null | undefined): string | undefined {
  const t = (raw || "").trim();
  if (!t) return undefined;
  // Reject accidental full meta tags pasted into env.
  if (/[<>\s]/.test(t)) return undefined;
  if (t.length > 120) return undefined;
  return t;
}

/**
 * Next.js `metadata.verification` payload.
 * Returns undefined when nothing configured (omit from metadata).
 */
export function buildSiteVerificationMetadata(
  input: VerificationEnv = readVerificationEnv(),
): Metadata["verification"] | undefined {
  const google = cleanToken(input.googleSiteVerification);
  const bing = cleanToken(input.bingSiteVerification);
  if (!google && !bing) return undefined;

  const verification: NonNullable<Metadata["verification"]> = {};
  if (google) verification.google = google;
  if (bing) {
    verification.other = {
      ...(verification.other || {}),
      "msvalidate.01": bing,
    };
  }
  return verification;
}
