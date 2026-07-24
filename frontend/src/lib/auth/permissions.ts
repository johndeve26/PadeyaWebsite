import type { User } from "@/lib/auth/types";

/** Mirrors backend PERMISSION_IMPLIES for shared umbrellas used in UI. */
const PERMISSION_IMPLIES: Record<string, readonly string[]> = {
  "merch.manage_own": ["merch.view_fulfillment", "merch.fulfill"],
  "merch.fulfill": ["merch.view_fulfillment"],
  "admin.users.view": [
    "admin.users.view_activity",
    "admin.users.view_audit",
  ],
  /** Legacy umbrella until BE fully splits restriction perms. */
  "admin.users.restrict": [
    "admin.users.view_restrictions",
    "admin.users.add_restriction",
    "admin.users.revoke_restriction",
  ],
  "admin.finance.manage_fees": ["admin.finance.view_fees"],
  "admin.finance.manage_host_overrides": ["admin.finance.view_fees"],
  "admin.ai.manage_settings": [
    "admin.ai.test_connection",
    "admin.ai.manage_spend",
  ],
  "admin.settings.edit_runtime": [
    "admin.ai.manage_settings",
    "admin.ai.manage_providers",
    "admin.ai.test_connection",
  ],
  "admin.blog.edit": [
    "admin.blog.comments.edit_any",
    "admin.blog.comments.reply_any",
    "admin.blog.comments.moderate",
  ],
  "admin.blog.comments.moderate": [
    "admin.blog.comments.edit_any",
    "admin.blog.comments.reply_any",
  ],
  "admin.full_access": [],
};

function permissionCodesFor(user: User): Set<string> {
  const codes = new Set(user.permissions);
  if (codes.has("admin.full_access")) return codes;
  for (const [owned, implied] of Object.entries(PERMISSION_IMPLIES)) {
    if (codes.has(owned)) {
      for (const code of implied) codes.add(code);
    }
  }
  return codes;
}

export function userHasRole(user: User | null, ...roles: string[]): boolean {
  if (!user) return false;
  if (user.roles.includes("super_admin")) return true;
  return roles.some((role) => user.roles.includes(role));
}

export function userHasPermission(
  user: User | null,
  ...permissions: string[]
): boolean {
  if (!user) return false;
  if (user.permissions.includes("admin.full_access")) return true;
  const codes = permissionCodesFor(user);
  return permissions.some((code) => codes.has(code));
}
