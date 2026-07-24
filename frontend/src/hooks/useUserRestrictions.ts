"use client";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  USER_RESTRICTION_ACTION_MESSAGE,
  restrictionBlockMessage,
  userHasAnyRestriction,
  userHasRestriction,
  userRestrictionKeys,
} from "@/lib/user-restrictions";
import type { AccountRestriction } from "@/lib/account-status";

/** Signed-in restriction keys from /me session — never reasons/notes. */
export function useUserRestrictions() {
  const { user } = useAuth();
  const keys = userRestrictionKeys(user);

  return {
    keys,
    has: (code: AccountRestriction | string) => userHasRestriction(user, code),
    hasAny: (codes: readonly (AccountRestriction | string)[]) =>
      userHasAnyRestriction(user, codes),
    blockMessage: (code: AccountRestriction | string) =>
      restrictionBlockMessage(user, code),
    actionMessage: USER_RESTRICTION_ACTION_MESSAGE,
  };
}
