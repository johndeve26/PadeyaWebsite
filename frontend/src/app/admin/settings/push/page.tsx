"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { RequireAuth } from "@/components/auth/RequireAuth";

/**
 * Legacy alias — keep compatible.
 * Hub category lives at `/admin/settings/runtime/push`; specialist editor stays
 * at `/admin/push/settings` for VAPID secret management.
 */
function AdminSettingsPushRedirectInner() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin/settings/runtime/push");
  }, [router]);
  return null;
}

export default function AdminSettingsPushRedirect() {
  return (
    <RequireAuth roles={["super_admin"]}>
      <AdminSettingsPushRedirectInner />
    </RequireAuth>
  );
}
