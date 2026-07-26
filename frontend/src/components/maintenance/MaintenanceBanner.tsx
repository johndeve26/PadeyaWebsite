"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import type { PublicMaintenanceStatus } from "@/lib/maintenance-api";
import { fetchPublicMaintenanceStatus } from "@/lib/maintenance-public";

/** Global scheduled / active maintenance banner for app shells. */
export function MaintenanceBanner() {
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

  const copy = useMemo(() => {
    if (!status) return null;
    if (status.mode === "active" || status.mode === "read_only") {
      return (
        status.message ||
        "Pàdéyá is undergoing maintenance. We’ll be back soon."
      );
    }
    if (status.upcoming_schedule) {
      const when = new Date(status.upcoming_schedule.starts_at).toLocaleString();
      return `Scheduled maintenance begins at ${when}. Some features may be unavailable.`;
    }
    if (status.sections && status.sections.length > 0) {
      return `Some areas are under maintenance: ${status.sections
        .map((s) => s.label)
        .join(", ")}.`;
    }
    return null;
  }, [status]);

  if (!copy) return null;

  return (
    <div
      role="status"
      className="border-b border-amber-500/30 bg-amber-500/10 px-4 py-2 text-center text-sm text-heading"
    >
      <span>{copy} </span>
      <Link href="/maintenance" className="font-semibold underline-offset-2 hover:underline">
        Details
      </Link>
    </div>
  );
}
