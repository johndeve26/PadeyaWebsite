"use client";

import Link from "next/link";

import { Button } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import {
  draftCartItemCount,
  draftCartSubtotal,
  type MerchDraftCart,
} from "@/lib/merch-draft-cart";

type Props = {
  cart: MerchDraftCart | null;
  checkoutHref: string;
  allowMerchOnly?: boolean;
  onRemoveLine?: (variantId: string) => void;
  variant?: "sidebar" | "mobile-bar";
};

export function MerchCartSummary({
  cart,
  checkoutHref,
  allowMerchOnly = false,
  onRemoveLine,
  variant = "sidebar",
}: Props) {
  const count = draftCartItemCount(cart);
  const subtotal = draftCartSubtotal(cart);
  const empty = count === 0;

  if (variant === "mobile-bar") {
    if (empty) return null;
    return (
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 px-4 py-3 backdrop-blur-md lg:hidden">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-extrabold text-foreground">
              {count} item{count === 1 ? "" : "s"} · {formatNgn(subtotal)}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              Pickup at event
              {allowMerchOnly ? "" : " · add at ticket checkout"}
            </p>
          </div>
          <Link href={checkoutHref}>
            <Button size="sm">Checkout</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <aside className="rounded-[var(--radius-lg)] border border-border bg-card p-5 shadow-sm">
      <h2 className="text-lg font-extrabold tracking-tight text-foreground">
        Your merch cart
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        {empty
          ? "Add merch to start your order."
          : "Review items, then continue to checkout."}
      </p>

      {empty ? null : (
        <ul className="mt-4 max-h-64 space-y-3 overflow-y-auto">
          {cart?.lines.map((line) => (
            <li
              key={line.variantId}
              className="flex items-start justify-between gap-2 border-b border-border pb-3 last:border-0 last:pb-0"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-foreground">
                  {line.productName}
                </p>
                <p className="text-xs text-muted-foreground">
                  {line.variantLabel} · ×{line.quantity}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-sm font-extrabold text-foreground">
                  {formatNgn(line.unitPrice * line.quantity)}
                </p>
                {onRemoveLine ? (
                  <button
                    type="button"
                    onClick={() => onRemoveLine(line.variantId)}
                    className="text-[11px] font-bold text-muted-foreground underline-offset-2 hover:underline"
                  >
                    Remove
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 space-y-3 border-t border-border pt-4">
        <div className="flex items-center justify-between text-sm">
          <span className="font-bold text-muted-foreground">Subtotal</span>
          <span className="font-extrabold text-foreground">
            {formatNgn(subtotal)}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Pickup at the event by default. Shipping applies only when a product
          supports delivery and you choose it at checkout.
        </p>
        <Link href={checkoutHref} className="block" aria-disabled={empty}>
          <Button className="w-full" disabled={empty}>
            Checkout
          </Button>
        </Link>
      </div>
    </aside>
  );
}
