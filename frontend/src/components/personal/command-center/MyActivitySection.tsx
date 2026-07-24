"use client";

import Link from "next/link";

import { SectionLabel } from "@/components/personal/command-center/SectionLabel";
import { SkeletonLoader } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  buildActivityChips,
  hasAttentionSignals,
  type ActivityChip,
} from "@/lib/personal-command-center";
import type { Order, Ticket } from "@/lib/types/commerce";
import type { RefundRequest } from "@/lib/types/finance";
import type { MerchFulfillment } from "@/lib/types/merch";

export function MyActivitySection({
  loading,
  tickets,
  orders,
  merch,
  refunds,
  cartLines,
}: {
  loading: boolean;
  tickets: Ticket[] | null;
  orders: Order[] | null;
  merch: MerchFulfillment[] | null;
  refunds: RefundRequest[] | null;
  cartLines: number;
}) {
  if (loading || !tickets || !orders || !merch) {
    return (
      <section className="min-w-0 space-y-3">
        <SectionLabel>My activity</SectionLabel>
        <SkeletonLoader lines={2} />
      </section>
    );
  }

  if (
    !hasAttentionSignals({
      tickets,
      orders,
      merch,
      refunds: refunds ?? [],
      cartLines,
    })
  ) {
    return null;
  }

  const chips = buildActivityChips({
    tickets,
    orders,
    merch,
    refunds: refunds ?? [],
    cartLines,
  });

  return (
    <section className="min-w-0 space-y-3">
      <SectionLabel>My activity</SectionLabel>
      <ul className="m-0 grid min-w-0 list-none grid-cols-2 gap-2 p-0 sm:grid-cols-4">
        {chips.map((chip) => (
          <ActivityChipLink key={chip.key} chip={chip} />
        ))}
      </ul>
    </section>
  );
}

function ActivityChipLink({ chip }: { chip: ActivityChip }) {
  return (
    <li className="min-w-0">
      <Link
        href={chip.href}
        className={cn(
          "flex h-full min-w-0 flex-col gap-1 rounded-[var(--radius-lg)] border px-3 py-3 transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          chip.emphasize
            ? "border-primary/40 bg-primary/10 text-foreground"
            : "border-border bg-card text-foreground hover:bg-surface-muted dark:bg-surface-elevated",
        )}
      >
        <span className="truncate text-[11px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
          {chip.label}
        </span>
        <span className="break-words text-sm font-semibold leading-snug">
          {chip.value}
        </span>
      </Link>
    </li>
  );
}
