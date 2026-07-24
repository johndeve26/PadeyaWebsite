/** App shells (buyer/host/admin/support staff/connect/staff). */
export const WORKSPACE_PREFIXES = [
  "/dashboard",
  "/host",
  "/admin",
  "/support",
  "/connect",
  "/staff",
] as const;

/**
 * Public Support Center routes use marketing chrome + footer.
 * Staff desk/cases/refunds remain workspace shells under `/support/*`.
 */
export function isWorkspacePath(pathname: string) {
  if (
    pathname === "/support" ||
    pathname === "/support/new" ||
    pathname.startsWith("/support/tickets")
  ) {
    return false;
  }
  return WORKSPACE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}
