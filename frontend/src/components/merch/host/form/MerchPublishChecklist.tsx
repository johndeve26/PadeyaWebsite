"use client";

import { cn } from "@/lib/cn";

import type { MerchProductFormValues } from "./types";
import { variantSummary } from "./types";

export type ChecklistItem = {
  id: string;
  label: string;
  done: boolean;
};

export function buildPublishChecklist(
  values: MerchProductFormValues,
  eventSelected: boolean,
  options?: { requireEvent?: boolean },
): ChecklistItem[] {
  const summary = variantSummary(values);
  const fulfillment =
    values.pickup_enabled ||
    values.shipping_enabled ||
    values.print_on_demand_enabled;
  const requireEvent = options?.requireEvent !== false;

  return [
    {
      id: "event",
      label: requireEvent ? "Event selected" : "Shop context set",
      done: requireEvent ? eventSelected : true,
    },
    {
      id: "name",
      label: "Product name added",
      done: Boolean(values.name.trim()),
    },
    {
      id: "price",
      label: "Price added",
      done: Number(values.base_price) >= 0 && values.base_price.trim() !== "",
    },
    {
      id: "variants",
      label: "At least one variant",
      done: summary.totalVariants > 0,
    },
    {
      id: "inventory",
      label: "Inventory set",
      done: values.variants.every(
        (v) => v.inventory.trim() !== "" && Number(v.inventory) >= 0,
      ),
    },
    { id: "fulfillment", label: "Fulfillment selected", done: fulfillment },
    {
      id: "visibility",
      label: "Public visibility configured",
      done: Boolean(values.storefront_visibility),
    },
  ];
}

type Props = {
  items: ChecklistItem[];
  className?: string;
};

export function MerchPublishChecklist({ items, className }: Props) {
  const doneCount = items.filter((i) => i.done).length;

  return (
    <div
      className={cn(
        "rounded-[var(--radius-lg)] border border-border bg-card p-4",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-extrabold text-foreground">
          Publish checklist
        </h3>
        <p className="text-xs font-bold text-muted-foreground">
          {doneCount}/{items.length}
        </p>
      </div>
      <ul className="mt-3 space-y-2">
        {items.map((item) => (
          <li key={item.id} className="flex items-start gap-2 text-sm">
            <span
              className={cn(
                "mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-extrabold",
                item.done
                  ? "bg-success-surface text-success-foreground"
                  : "bg-surface-muted text-muted-foreground",
              )}
              aria-hidden
            >
              {item.done ? "✓" : "·"}
            </span>
            <span
              className={
                item.done ? "text-foreground" : "text-muted-foreground"
              }
            >
              {item.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
