"use client";

import { LegacyPublicPageRenderer } from "@/components/legacy/LegacyPublicPageRenderer";
import type { LegacyPage } from "@/lib/types/legacy";

/** Client island for interactive Host Legacy (follow, message, CTAs). */
export function LegacyPublicClient({ page }: { page: LegacyPage }) {
  return <LegacyPublicPageRenderer page={page} />;
}
