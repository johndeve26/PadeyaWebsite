"use client";

import { LegacyPublicPageRenderer } from "@/components/legacy/LegacyPublicPageRenderer";
import type { LegacyPage } from "@/lib/types/legacy";

/** @deprecated Prefer LegacyPublicPageRenderer — kept for existing imports. */
export function LegacyPageView({ page }: { page: LegacyPage }) {
  return <LegacyPublicPageRenderer page={page} />;
}
