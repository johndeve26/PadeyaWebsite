/** End-user account restriction helpers — keys only from /me or session. */

import type { AccountRestriction } from "@/lib/account-status";
import { normalizeAccountRestrictions } from "@/lib/account-status";

/** Safe copy shown to restricted users — never admin reason or internal notes. */
export const USER_RESTRICTION_ACTION_MESSAGE =
  "This action isn’t available on your account.";

export type RestrictionKeySource = {
  account_restrictions?: readonly string[] | null;
} | null | undefined;

/** Active restriction keys from session/me. Safe when absent. */
export function userRestrictionKeys(
  source: RestrictionKeySource,
): AccountRestriction[] {
  try {
    return normalizeAccountRestrictions(source?.account_restrictions);
  } catch {
    return [];
  }
}

export function userHasRestriction(
  source: RestrictionKeySource,
  code: AccountRestriction | string,
): boolean {
  return userRestrictionKeys(source).includes(code as AccountRestriction);
}

export function userHasAnyRestriction(
  source: RestrictionKeySource,
  codes: readonly (AccountRestriction | string)[],
): boolean {
  const keys = new Set<string>(userRestrictionKeys(source));
  return codes.some((code) => keys.has(code));
}

/** Message when blocked; null when allowed. */
export function restrictionBlockMessage(
  source: RestrictionKeySource,
  code: AccountRestriction | string,
): string | null {
  return userHasRestriction(source, code)
    ? USER_RESTRICTION_ACTION_MESSAGE
    : null;
}
