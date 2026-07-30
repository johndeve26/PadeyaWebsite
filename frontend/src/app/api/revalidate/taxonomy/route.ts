import { revalidatePath, revalidateTag } from "next/cache";
import { NextResponse } from "next/server";

import {
  authorizeRevalidateRequest,
  getRevalidateSecret,
  revalidateMisconfiguredResponse,
  revalidateUnauthorizedResponse,
} from "@/lib/cache/revalidate-auth";

/**
 * Bust public discovery surfaces after taxonomy image / term changes.
 * Authenticated with REVALIDATE_SECRET (Bearer or x-revalidate-secret).
 */
export async function POST(request: Request) {
  if (!getRevalidateSecret()) {
    return revalidateMisconfiguredResponse();
  }
  if (!authorizeRevalidateRequest(request)) {
    return revalidateUnauthorizedResponse();
  }

  revalidateTag("taxonomy", "max");
  revalidatePath("/events");
  revalidatePath("/events/c", "layout");
  revalidatePath("/events/city", "layout");
  revalidatePath("/events/state", "layout");
  revalidatePath("/events/area", "layout");
  revalidatePath("/events/country", "layout");
  revalidatePath("/");
  revalidatePath("/sitemap.xml");

  return NextResponse.json({ ok: true, revalidated: true });
}
