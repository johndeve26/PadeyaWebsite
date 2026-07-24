"use client";

import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMaintenanceHistory } from "@/lib/maintenance-api";

export default function AdminMaintenanceHistoryPage() {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetchMaintenanceHistory();
        setItems(res.items);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Failed to load");
      }
    })();
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Platform"
      title="Maintenance history"
      description="Audit trail for maintenance mode changes (no secrets)."
    >
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      <ul className="divide-y divide-border rounded-[var(--radius-md)] border border-border">
        {items.map((row) => (
          <li key={String(row.id)} className="px-4 py-3 text-sm">
            <p className="font-semibold text-heading">{String(row.action)}</p>
            <p className="text-xs text-muted-foreground">
              {String(row.created_at || "")}
            </p>
          </li>
        ))}
        {!items.length && !error ? (
          <li className="px-4 py-6 text-sm text-muted-foreground">No entries yet.</li>
        ) : null}
      </ul>
    </DashboardShell>
  );
}
