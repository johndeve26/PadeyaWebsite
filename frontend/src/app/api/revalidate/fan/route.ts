import { revalidatePath, revalidateTag } from "next/cache";
import { NextResponse } from "next/server";

import {
  authorizeRevalidateRequest,
  getRevalidateSecret,
  revalidateMisconfiguredResponse,
  revalidateUnauthorizedResponse,
} from "@/lib/cache/revalidate-auth";

type Body = {
  username?: string;
  /** When username changed, also purge the previous public path. */
  previous_username?: string;
};

function normalizeUsername(raw: string | undefined): string | null {
  if (!raw) return null;
  const u = decodeURIComponent(raw).replace(/^@/, "").trim().toLowerCase();
  if (!u || u.length > 64 || !/^[a-z0-9_]+$/.test(u)) return null;
  return u;
}

/**
 * Secure server-to-server purge for Fan Passport public surfaces.
 *
 * HTML for `/f/{username}` is intentionally no-store (privacy). This route
 * still busts directory + sitemap ISR and any residual path cache after
 * visibility / username / admin-hide changes.
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

  const username = normalizeUsername(body.username);
  const previous = normalizeUsername(body.previous_username);

  if (username) {
    revalidatePath(`/f/${encodeURIComponent(username)}`);
  }
  if (previous && previous !== username) {
    revalidatePath(`/f/${encodeURIComponent(previous)}`);
  }

  // Next 16 requires a cacheLife profile as the second argument.
  revalidateTag("fans", "max");
  revalidateTag("fan-directory", "max");
  revalidatePath("/fans");
  revalidatePath("/sitemap.xml");

  return NextResponse.json({
    revalidated: true,
    username,
    previous_username: previous,
    now: Date.now(),
  });
}
