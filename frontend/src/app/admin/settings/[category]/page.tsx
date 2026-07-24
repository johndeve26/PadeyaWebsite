"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

const ALLOWED = new Set([
  "ai",
  "payments",
  "storage",
  "integrations",
  "notifications",
  "feature-toggles",
  "features",
  "security-runtime",
  "system-status",
]);

/** Legacy flat paths → `/admin/settings/runtime/[category]`. */
export default function AdminSettingsLegacyCategoryRedirect() {
  const router = useRouter();
  const params = useParams();
  const category = String(params.category ?? "");

  useEffect(() => {
    if (ALLOWED.has(category)) {
      router.replace(`/admin/settings/runtime/${category}`);
    } else {
      router.replace("/admin/settings/runtime");
    }
  }, [category, router]);

  return null;
}
