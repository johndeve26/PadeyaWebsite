/** Matches backend Fan Passport username rules. */
export const PASSPORT_USERNAME_PATTERN = /^[a-z0-9_]{3,32}$/;

export function normalizePassportUsername(raw: string): string {
  return raw.trim().toLowerCase().replace(/^@+/, "").replace(/[^a-z0-9_]/g, "_").replace(/_+/g, "_").replace(/^_|_$/g, "").slice(0, 32);
}
