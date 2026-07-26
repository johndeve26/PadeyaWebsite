import { revalidatePath, revalidateTag } from "next/cache";
import { NextResponse } from "next/server";

import {
  authorizeRevalidateRequest,
  getRevalidateSecret,
  revalidateMisconfiguredResponse,
  revalidateUnauthorizedResponse,
} from "@/lib/cache/revalidate-auth";

type Body = {
  /** Event slug, e.g. demo-food-and-flow */
  slug?: string;
};

function normalizeSlug(raw: string | undefined): string | null {
  if (!raw) return null;
  const s = decodeURIComponent(raw).trim().toLowerCase();
  if (!s || s.length > 120 || !/^[a-z0-9-]+$/.test(s)) return null;
  return s;
}

/**
 * Secure server-to-server purge for Event Memories public surfaces.
 *
 * Busts `/memories`, `/events/{slug}/memories`, and the event page preview
 * after photo upload / delete / hide / cover / external gallery changes.
 * Does not touch Fan Passport privacy caches.
 */
export async function POST(request: Request) {
  if (!getRevalidateSecret()) {
    return revalidateMisconfiguredResponse();
  }
  if (!authorizeRevalidateRequest(request)) {
    return revalidateUnauthorizedResponse();
  }

  let body: Body = {};
  try {
    body = (await request.json()) as Body;
  } catch {
    body = {};
  }

  const slug = normalizeSlug(body.slug);

  revalidateTag("memories", "max");
  revalidateTag("memories-albums", "max");
  revalidatePath("/memories");

  if (slug) {
    revalidateTag(`memories-${slug}`, "max");
    revalidateTag(`event-${slug}`, "max");
    revalidatePath(`/events/${encodeURIComponent(slug)}`);
    revalidatePath(`/events/${encodeURIComponent(slug)}/memories`);
  }

  return NextResponse.json({
    revalidated: true,
    slug,
    now: Date.now(),
  });
}
