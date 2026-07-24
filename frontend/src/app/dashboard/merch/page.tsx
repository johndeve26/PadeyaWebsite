"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { SkeletonLoader } from "@/components/ui";

/** Legacy path — redirects to `/dashboard/merchandise`. */
export default function LegacyBuyerMerchRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard/merchandise");
  }, [router]);

  return (
    <DashboardShell
      tone="soft"
      title="My merch"
      description="Taking you to your merchandise wallet…"
    >
      <SkeletonLoader lines={3} />
    </DashboardShell>
  );
}
