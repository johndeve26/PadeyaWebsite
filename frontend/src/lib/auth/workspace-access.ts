import type { User } from "@/lib/auth/types";
import { userHasRole } from "@/lib/auth/permissions";

/** Roles that can open `/admin` (keep in sync with `app/admin/layout.tsx`). */
export const ADMIN_PANEL_ROLES = [
  "super_admin",
  "admin",
  "admin_staff",
  "finance_admin",
  "support_agent",
  "moderation",
  "operations",
  "marketing",
] as const;

/** Roles that can open staff Support desk (`/support/desk`). */
export const SUPPORT_DESK_ROLES = ["support_agent", "super_admin"] as const;

export const ADMIN_PANEL_SWITCHER_LABEL = "Admin panel";
export const SUPPORT_DESK_SWITCHER_LABEL = "Support desk";

export function canAccessAdminPanel(
  user: User | null | undefined,
  isImpersonating = false,
): boolean {
  if (!user || isImpersonating) return false;
  return userHasRole(user, ...ADMIN_PANEL_ROLES);
}

export function canAccessSupportDesk(
  user: User | null | undefined,
  isImpersonating = false,
): boolean {
  if (!user || isImpersonating) return false;
  return userHasRole(user, ...SUPPORT_DESK_ROLES);
}
