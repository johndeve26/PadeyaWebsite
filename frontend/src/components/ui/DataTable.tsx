import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { EmptyState } from "./EmptyState";
import { MobileDataCard } from "./MobileDataCard";

export type DataTableColumn<T> = {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
  /** Prefer showing this column in the mobile card title row */
  primary?: boolean;
};

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  emptyTitle = "Nothing here yet",
  emptyDescription,
  className = "",
  mobileCard,
}: {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyTitle?: string;
  emptyDescription?: string;
  className?: string;
  /** Optional custom mobile card; defaults to stacked label/value rows */
  mobileCard?: (row: T) => ReactNode;
}) {
  if (rows.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  const primaryCol = columns.find((c) => c.primary) ?? columns[0];

  return (
    <div className={cn("min-w-0 space-y-3", className)}>
      {/* Cards through tablet — dense tables start at laptop */}
      <div className="space-y-3 lg:hidden">
        {rows.map((row) =>
          mobileCard ? (
            <div key={rowKey(row)} className="min-w-0">
              {mobileCard(row)}
            </div>
          ) : (
            <MobileDataCard
              key={rowKey(row)}
              title={primaryCol ? primaryCol.cell(row) : undefined}
              rows={columns
                .filter((col) => col.key !== primaryCol?.key)
                .map((col) => ({
                  label: col.header,
                  value: col.cell(row),
                }))}
            />
          ),
        )}
      </div>

      <div className="hidden min-w-0 overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card shadow-[var(--shadow-soft)] dark:bg-surface-elevated dark:shadow-[var(--shadow)] lg:block">
        <div className="overflow-x-auto overscroll-x-contain">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-border-strong/30 bg-surface-inset">
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={cn(
                      "whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground",
                      col.className,
                    )}
                  >
                    {col.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={rowKey(row)}
                  className="border-b border-border last:border-0 transition-colors hover:bg-surface-muted focus-within:bg-surface-muted/80"
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        "px-4 py-3.5 align-middle text-foreground",
                        col.className,
                      )}
                    >
                      <div className="min-w-0 max-w-[18rem] break-words">
                        {col.cell(row)}
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
