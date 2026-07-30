import { NextResponse } from "next/server";

import { getApiBaseUrl } from "@/lib/api-base";
import {
  guessImageContentType,
  isAllowedInlinePreviewUrl,
} from "@/lib/media-preview";

export const runtime = "nodejs";

/**
 * Stream allowlisted public media with Content-Disposition: inline so browsers
 * preview in a tab instead of downloading (CDN objects may lack that header).
 */
export async function GET(request: Request) {
  const raw = new URL(request.url).searchParams.get("url")?.trim() || "";
  if (!raw || !isAllowedInlinePreviewUrl(raw)) {
    return NextResponse.json({ detail: "URL not allowed" }, { status: 400 });
  }

  let upstreamUrl = raw;
  if (raw.startsWith("/media/")) {
    const base = getApiBaseUrl().replace(/\/$/, "");
    upstreamUrl = `${base}${raw}`;
  }

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      redirect: "follow",
      headers: { Accept: "image/*,*/*" },
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ detail: "Failed to fetch media" }, { status: 502 });
  }

  if (!upstream.ok) {
    return NextResponse.json(
      { detail: `Upstream returned ${upstream.status}` },
      { status: 502 },
    );
  }

  const upstreamType = (upstream.headers.get("content-type") || "")
    .split(";")[0]
    .trim()
    .toLowerCase();
  const contentType =
    upstreamType.startsWith("image/")
      ? upstreamType
      : guessImageContentType(raw);

  const headers = new Headers();
  headers.set("Content-Type", contentType);
  headers.set("Content-Disposition", "inline");
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Cache-Control", "private, max-age=60");

  return new NextResponse(upstream.body, {
    status: 200,
    headers,
  });
}
