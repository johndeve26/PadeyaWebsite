import { NextResponse, type NextRequest } from "next/server";

/**
 * Public host surfaces live at /@username[…].
 * App Router cannot use @ as a URL segment, so rewrite to /u/[username][…].
 * Covers Legacy, Vault, and merch storefront (/@user/merch).
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!pathname.startsWith("/@")) {
    return NextResponse.next();
  }

  const remainder = pathname.slice(2); // username/...
  const slash = remainder.indexOf("/");
  const username = slash === -1 ? remainder : remainder.slice(0, slash);
  const rest = slash === -1 ? "" : remainder.slice(slash); // /vault|/merch|…
  if (!username) {
    return NextResponse.next();
  }

  const url = request.nextUrl.clone();
  url.pathname = `/u/${username}${rest}`;
  return NextResponse.rewrite(url);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
