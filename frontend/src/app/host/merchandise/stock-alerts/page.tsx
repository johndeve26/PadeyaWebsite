"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Badge, Button, EmptyState, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchHostStockAlerts,
  type HostStockAlert,
} from "@/lib/merch-api";

type StockAlertRow = HostStockAlert;

const SECTIONS: { type: string; title: string; empty: string; tone: "warning" | "danger" | "success" }[] =
  [
    {
      type: "low_stock",
      title: "Low stock",
      empty: "No low-stock alerts.",
      tone: "warning",
    },
    {
      type: "sold_out",
      title: "Sold out",
      empty: "No sold-out alerts.",
      tone: "danger",
    },
    {
      type: "restocked",
      title: "Restocked",
      empty: "No recent restocks.",
      tone: "success",
    },
  ];

function editHref(row: StockAlertRow): string {
  if (row.event_id) {
    return `/host/events/${row.event_id}/merchandise/${row.product_id}/edit`;
  }
  return `/host/merchandise/${row.product_id}/edit`;
}

function AlertSection({
  title,
  empty,
  tone,
  rows,
}: {
  title: string;
  empty: string;
  tone: "warning" | "danger" | "success";
  rows: StockAlertRow[];
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">
          {title}
        </h2>
        <Badge tone={tone} size="sm">
          {rows.length}
        </Badge>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul className="divide-y divide-border border-y border-border">
          {rows.map((row) => {
            const stock =
              row.current_available ?? row.available_snapshot ?? null;
            return (
              <li
                key={row.id}
                className="flex flex-wrap items-center justify-between gap-3 py-3"
              >
                <div className="min-w-0">
                  <Link
                    href={editHref(row)}
                    className="font-semibold text-foreground underline-offset-2 hover:underline"
                  >
                    {row.product_name || "Product"}
                    {row.variant_label ? ` · ${row.variant_label}` : ""}
                  </Link>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Current stock: {stock === null ? "—" : stock}
                    {row.threshold != null ? ` · Threshold: ${row.threshold}` : ""}
                  </p>
                </div>
                <Link href={editHref(row)}>
                  <Button size="sm" variant="secondary">
                    Edit inventory
                  </Button>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export default function HostStockAlertsPage() {
  const [rows, setRows] = useState<StockAlertRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchHostStockAlerts();
        if (active) setRows(data as StockAlertRow[]);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Could not load alerts",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const grouped = useMemo(() => {
    const map: Record<string, StockAlertRow[]> = {};
    for (const section of SECTIONS) map[section.type] = [];
    for (const row of rows ?? []) {
      if (!map[row.alert_type]) map[row.alert_type] = [];
      map[row.alert_type].push(row);
    }
    return map;
  }, [rows]);

  const otherRows = useMemo(() => {
    const known = new Set(SECTIONS.map((s) => s.type));
    return (rows ?? []).filter((r) => !known.has(r.alert_type));
  }, [rows]);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title="Stock alerts"
        description="Low stock, sold out, and restock signals for your Pàdéyá merch."
        actions={
          <Link href="/host/merchandise">
            <Button size="sm" variant="secondary">
              All merch
            </Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Unavailable">
            {error}
          </Alert>
        ) : null}
        {rows === null ? <SkeletonLoader lines={4} /> : null}
        {rows && rows.length === 0 ? (
          <EmptyState
            title="No open alerts"
            description="Inventory looks healthy for now."
          />
        ) : null}
        {rows && rows.length > 0 ? (
          <div className="space-y-8">
            {SECTIONS.map((section) => (
              <AlertSection
                key={section.type}
                title={section.title}
                empty={section.empty}
                tone={section.tone}
                rows={grouped[section.type] ?? []}
              />
            ))}
            {otherRows.length > 0 ? (
              <AlertSection
                title="Other risks"
                empty=""
                tone="warning"
                rows={otherRows}
              />
            ) : null}
          </div>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
