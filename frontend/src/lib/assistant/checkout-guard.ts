/**
 * Hide the assistant on checkout surfaces so it never covers payment CTAs.
 */
export function shouldHideAssistant(pathname: string | null | undefined): boolean {
  if (!pathname) return false;
  const path = pathname.split("?")[0] || pathname;

  if (path === "/checkout" || path.startsWith("/checkout/")) return true;

  // /events/:id/checkout and nested checkout steps
  if (/^\/events\/[^/]+\/checkout(?:\/|$)/.test(path)) return true;

  // /merch/:id/checkout and nested checkout steps
  if (/^\/merch\/[^/]+\/checkout(?:\/|$)/.test(path)) return true;

  return false;
}
