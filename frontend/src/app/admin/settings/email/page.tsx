"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Legacy path → runtime email category (links through to specialist). */
export default function AdminSettingsEmailRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin/settings/runtime/email");
  }, [router]);
  return null;
}
