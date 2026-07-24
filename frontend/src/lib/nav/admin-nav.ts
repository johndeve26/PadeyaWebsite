import type { User } from "../auth/types";
import { userHasPermission } from "../auth/permissions";
import {
  adminNavGroups as allAdminNavGroups,
  flattenNavGroups,
  type NavGroup,
  type NavItem,
} from "./workspace";

/** Whether an admin nav item is visible for this user. */
export function canSeeAdminNavItem(
  user: User | null,
  item: NavItem,
): boolean {
  if (!user) return false;
  if (!item.permissions?.length) return true;
  return userHasPermission(user, ...item.permissions);
}

/** Grouped admin nav filtered by item-level permissions. */
export function navGroupsForAdmin(user: User | null): NavGroup[] {
  return allAdminNavGroups
    .map((group) => ({
      label: group.label,
      items: group.items.filter((item) => canSeeAdminNavItem(user, item)),
    }))
    .filter((group) => group.items.length > 0);
}

/** Flat admin nav for mobile topbar. */
export function navForAdmin(user: User | null): NavItem[] {
  return flattenNavGroups(navGroupsForAdmin(user));
}
