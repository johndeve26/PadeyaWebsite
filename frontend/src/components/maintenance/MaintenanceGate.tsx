"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { userHasPermission } from "@/lib/auth/permissions";
import {
  fetchPublicMaintenanceStatus,
  type PublicMaintenanceStatus,
} from "@/lib/maintenance-api";

const ALLOW_PREFIXES = [
  "/maintenance",
  "/admin",
  "/login",
  "/register",
  "/auth",
  "/forgot-password",
  "/reset-password",
];

/**
 * Public visitors are redirected to /maintenance when full-site mode is active.
 * Logged-in users stay on-site (banner + API enforcement). Staff with
 * maintenance permissions can browse freely including admin.
 */
export function MaintenanceGate({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "/";
  const router = useRouter();
  const { user, loading } = useAuth();
  const [status, setStatus] = useState<PublicMaintenanceStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetchPublicMaintenanceStatus();
        if (!cancelled) setStatus(res);
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (loading || !status) return;
    if (status.mode !== "active") return;
    if (ALLOW_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
      return;
    }
    if (
      user &&
      userHasPermission(
        user,
        "admin.full_access",
        "admin.maintenance.view",
        "admin.maintenance.manage",
        "admin.maintenance.bypass",
      )
    ) {
      return;
    }
    // Logged-in fans stay (notice via banner); anonymous → maintenance page.
    if (!user) {
      router.replace("/maintenance");
    }
  }, [loading, status, pathname, user, router]);

  return <>{children}</>;
}
