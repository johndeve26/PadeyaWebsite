"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Hub alias → runtime settings dashboard. */
export default function AdminSettingsIndexRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin/settings/runtime");
  }, [router]);
  return null;
}
