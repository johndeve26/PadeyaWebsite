/**
 * Canonical Vault product copy for Pàdéyá UI.
 * Keep docs/VAULT.md in sync when changing the definition.
 */

export const VAULT_NAME = "Vault";

/** One-sentence product definition. */
export const VAULT_DEFINITION =
  "Vault is exclusive host content fans can unlock through following, buying tickets, attending events, VIP access, or one-time purchase.";

/** Short line for section descriptions and studio shells. */
export const VAULT_TAGLINE =
  "Exclusive host content unlocked by follow, ticket, attendance, VIP, or purchase.";

/** Host studio supporting sentence. */
export const VAULT_HOST_STUDIO_DESCRIPTION =
  "Create exclusive drops fans unlock by following you, buying tickets, checking in, VIP access, or a one-time purchase — then feature them on your Legacy Page.";

/** Public Vault catalog subtitle. */
export const VAULT_PUBLIC_DESCRIPTION =
  "Unlock behind-the-scenes content, early-access drops, and ticket-holder rewards from this host.";

/** Public Vault page headline — pass host display name. */
export function vaultPublicHeadline(displayName: string): string {
  const name = displayName.trim() || "this host";
  return `Exclusive drops from ${name}`;
}

/** Legacy page Vault block fallback description. */
export const VAULT_LEGACY_BLOCK_DESCRIPTION =
  "Exclusive drops fans unlock by follow, ticket, attendance, VIP, or purchase.";

/** Empty-state examples for hosts and empty public catalogs. */
export const VAULT_EXAMPLES = [
  "Behind the scenes from a completed event",
  "Unreleased DJ set",
  "Early-access ticket drop",
  "VIP photo gallery",
  "Ticket-holder recap video",
  "Sponsor-supported content drop",
  "Private announcement",
  "Discount code drop",
] as const;

export const VAULT_UNLOCK_PATHS = [
  "Following the host",
  "Buying a ticket",
  "Attending / checking in",
  "VIP access",
  "One-time purchase",
] as const;
