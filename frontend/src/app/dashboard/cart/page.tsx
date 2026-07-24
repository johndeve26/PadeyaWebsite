"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, EmptyState, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchBuyerCart, removeBuyerCartItem } from "@/lib/merch-api";
import { resolveCartCheckoutPath } from "@/lib/personal-command-center";

type Cart = NonNullable<Awaited<ReturnType<typeof fetchBuyerCart>>>;

export default function BuyerCartPage() {
  const [cart, setCart] = useState<Cart | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const row = await fetchBuyerCart();
        if (active) setCart(row);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Could not load cart");
          setCart(null);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const items = cart?.items ?? [];
  const isEmpty =
    cart == null || cart.id == null || items.length === 0 || cart.status === "empty";
  const resumePath = resolveCartCheckoutPath(cart);

  async function onRemove(itemId: string) {
    setRemovingId(itemId);
    setError(null);
    try {
      const next = await removeBuyerCartItem(itemId);
      setCart(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not update cart");
    } finally {
      setRemovingId(null);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Cart"
      title="Your merch cart"
      description="Saved Pàdéyá event merch — nothing here is purchased until checkout payment succeeds."
      actions={
        <div className="flex flex-wrap gap-2">
          {resumePath && !isEmpty ? (
            <Link href={resumePath}>
              <Button size="sm">Resume checkout</Button>
            </Link>
          ) : null}
          <Link href="/dashboard/merchandise">
            <Button variant="secondary" size="sm">
              My merch
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Cart unavailable">
          {error}
        </Alert>
      ) : null}

      {cart === undefined ? <SkeletonLoader lines={3} /> : null}

      {cart !== undefined && isEmpty ? (
        <EmptyState
          title="Cart is empty"
          description="Add event merch from a host storefront or event page."
        />
      ) : null}

      {cart && !isEmpty ? (
        <ul className="space-y-3">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-2 border-b border-border py-3"
            >
              <div>
                <p className="font-semibold text-foreground">
                  {item.product_name_snapshot}
                </p>
                <p className="text-sm text-muted-foreground">
                  {item.variant_label_snapshot} · Qty {item.quantity}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <p className="text-sm font-bold">
                  ₦{Number(item.unit_price_snapshot).toLocaleString()}
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={removingId === item.id}
                  onClick={() => void onRemove(item.id)}
                >
                  Remove
                </Button>
              </div>
            </li>
          ))}
          <li className="flex flex-wrap items-center justify-between gap-3 pt-3">
            <p className="text-xs text-muted-foreground">
              Status: {cart.status}. Complete checkout to pay — this cart never
              marks items as purchased on its own.
            </p>
            {resumePath ? (
              <Link href={resumePath}>
                <Button size="sm">Resume checkout</Button>
              </Link>
            ) : (
              <Link href="/events">
                <Button size="sm" variant="secondary">
                  Browse events
                </Button>
              </Link>
            )}
          </li>
        </ul>
      ) : null}
    </DashboardShell>
  );
}
