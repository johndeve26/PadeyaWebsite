"use client";

import { useEffect, useState } from "react";

import {
  fetchPublicMaintenanceStatus,
  type PublicMaintenanceStatus,
} from "@/lib/maintenance-api";

/** Inline notice when a specific platform section is under maintenance or read-only. */
export function SectionMaintenanceNotice({
  sectionKey,
  className = "",
}: {
  sectionKey: string;
  className?: string;
}) {
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

  if (!status) return null;

  if (status.mode === "read_only") {
    return (
      <div
        role="status"
        className={`rounded-[var(--radius-md)] border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-heading ${className}`}
      >
        Pàdéyá is in read-only mode. You can browse, but changes are temporarily
        disabled.
      </div>
    );
  }

  const section = status.sections?.find((s) => s.key === sectionKey);
  if (!section) return null;

  return (
    <div
      role="status"
      className={`rounded-[var(--radius-md)] border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-heading ${className}`}
    >
      <p className="font-semibold">{section.title || section.label}</p>
      <p className="mt-1 text-muted-foreground">
        {section.message ||
          (section.mode === "read_only"
            ? "This section is temporarily read-only."
            : "This section is temporarily under maintenance.")}
      </p>
    </div>
  );
}
