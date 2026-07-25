import type { Metadata } from "next";

/** Shared robots directive for private / auth / checkout surfaces. */
export const NOINDEX_ROBOTS = {
  index: false,
  follow: false,
  googleBot: { index: false, follow: false },
} as const satisfies NonNullable<Metadata["robots"]>;

/**
 * Soft noindex for public duplicate/filter surfaces (facets, search aliases).
 * Keep follow so equity can flow to the canonical hub.
 */
export const NOINDEX_FOLLOW_ROBOTS = {
  index: false,
  follow: true,
} as const satisfies NonNullable<Metadata["robots"]>;

/**
 * Explicit allow indexing. Must be set on public pages — returning
 * `robots: undefined` from generateMetadata clears parent root robots in Next.js.
 */
export const INDEXABLE_ROBOTS = {
  index: true,
  follow: true,
} as const satisfies NonNullable<Metadata["robots"]>;

/** Layout/page metadata for entire private subtrees. */
export function privateAreaMetadata(title: string): Metadata {
  return {
    title,
    robots: NOINDEX_ROBOTS,
  };
}
