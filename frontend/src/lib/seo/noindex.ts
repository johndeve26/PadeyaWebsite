import type { Metadata } from "next";

/** Shared robots directive for private / auth / checkout surfaces. */
export const NOINDEX_ROBOTS = {
  index: false,
  follow: false,
  googleBot: { index: false, follow: false },
} as const satisfies NonNullable<Metadata["robots"]>;

/** Layout/page metadata for entire private subtrees. */
export function privateAreaMetadata(title: string): Metadata {
  return {
    title,
    robots: NOINDEX_ROBOTS,
  };
}
