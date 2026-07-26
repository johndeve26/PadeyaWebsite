/**
 * Shared auth for server-to-server Next.js revalidation routes.
 *
 * Never expose unauthenticated purge endpoints. Callers must send:
 *   Authorization: Bearer <REVALIDATE_SECRET>
 * or:
 *   x-revalidate-secret: <REVALIDATE_SECRET>
 */

import { timingSafeEqual } from "node:crypto";

export function getRevalidateSecret(): string {
  return (process.env.REVALIDATE_SECRET || "").trim();
}

export function authorizeRevalidateRequest(request: Request): boolean {
  const secret = getRevalidateSecret();
  if (!secret) return false;

  const auth = request.headers.get("authorization") || "";
  const bearer = auth.toLowerCase().startsWith("bearer ")
    ? auth.slice(7).trim()
    : "";
  const header = (request.headers.get("x-revalidate-secret") || "").trim();
  const provided = bearer || header;
  if (!provided) return false;

  const a = Buffer.from(provided);
  const b = Buffer.from(secret);
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

export function revalidateUnauthorizedResponse(): Response {
  return Response.json({ detail: "Unauthorized" }, { status: 401 });
}

export function revalidateMisconfiguredResponse(): Response {
  return Response.json(
    { detail: "REVALIDATE_SECRET is not configured" },
    { status: 503 },
  );
}
