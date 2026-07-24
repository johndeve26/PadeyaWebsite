"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { canAccessHostPath } from "@/lib/host-access";

/**
 * Redirects team members away from host routes their permissions do not allow.
 */
export function HostAccessGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { active, loading, isOwner } = useHostWorkspace();

  useEffect(() => {
    if (loading || !active || isOwner) return;
    if (pathname.startsWith("/host/access-denied")) return;
    if (pathname.startsWith("/host/onboarding")) return;
    if (!canAccessHostPath(pathname, active)) {
      router.replace(
        `/host/access-denied?from=${encodeURIComponent(pathname)}`,
      );
    }
  }, [loading, active, isOwner, pathname, router]);

  return <>{children}</>;
}
