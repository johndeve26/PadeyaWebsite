"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

const ALLOWED = new Set([
  "ai",
  "payments",
  "storage",
  "integrations",
  "notifications",
  "security-runtime",
  "system-status",
]);

/** Legacy flat paths → `/admin/settings/runtime/[category]`. */
export default function AdminSettingsLegacyCategoryRedirect() {
  const router = useRouter();
  const params = useParams();
  const category = String(params.category ?? "");

  useEffect(() => {
    // Feature toggles are managed under AI controls, not runtime settings registry.
    if (category === "feature-toggles" || category === "features") {
      router.replace("/admin/ai/features");
      return;
    }
    if (ALLOWED.has(category)) {
      router.replace(`/admin/settings/runtime/${category}`);
    } else {
      router.replace("/admin/settings/runtime");
    }
  }, [category, router]);

  return null;
}
