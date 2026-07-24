"use client";

import { Badge, Input } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import { variantAvailable } from "@/lib/merch-stock";
import type { MerchCatalogProduct } from "@/lib/types/merch";

type Props = {
  products: MerchCatalogProduct[];
  quantities: Record<string, number>;
  onQuantityChange: (variantId: string, quantity: number) => void;
  unlocked: boolean;
  allowMerchOnly: boolean;
};

function productFulfillmentLabel(product: MerchCatalogProduct): string {
  const pickup = product.pickup_enabled !== false;
  const shipping = Boolean(product.shipping_enabled);
  if (pickup && shipping) return "Pickup or delivery";
  if (shipping) return "Delivery";
  return "Pickup at event";
}

export function CheckoutMerchAddons({
  products,
  quantities,
  onQuantityChange,
  unlocked,
  allowMerchOnly,
}: Props) {
  if (products.length === 0) return null;

  const anyShipping = products.some((p) => p.shipping_enabled);
  const anyPickup = products.some((p) => p.pickup_enabled !== false);

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h3 className="text-lg font-extrabold tracking-tight text-foreground">
          Event merch
        </h3>
        <p className="text-sm text-muted-foreground">
          Optional add-ons
          {anyShipping && anyPickup
            ? " · Choose pickup or delivery below when you check out."
            : anyShipping
              ? " · Delivery available for shippable items."
              : " · Pickup at the event."}
          {allowMerchOnly
            ? " Merch-only orders are allowed."
            : " Add a ticket first (or use an existing ticket for this event)."}
        </p>
      </div>

      <ul className="space-y-4">
        {products.map((product) => {
          const stockTotal = product.variants.reduce(
            (n, v) => n + variantAvailable(v),
            0,
          );
          return (
            <li
              key={product.id}
              className="space-y-3 border-b border-border pb-4 last:border-0 last:pb-0"
            >
              <div className="space-y-1">
                <p className="font-bold text-foreground">{product.name}</p>
                {product.short_description || product.description ? (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {product.short_description || product.description}
                  </p>
                ) : null}
                <div className="flex flex-wrap gap-1.5">
                  <Badge tone="outline" size="sm">
                    {productFulfillmentLabel(product)}
                  </Badge>
                  {product.requires_ticket ? (
                    <Badge tone="accent" size="sm">
                      Requires ticket
                    </Badge>
                  ) : null}
                  <Badge
                    tone={
                      stockTotal <= 0
                        ? "danger"
                        : stockTotal <= 5
                          ? "warning"
                          : "success"
                    }
                    size="sm"
                  >
                    {stockTotal <= 0
                      ? "Sold out"
                      : stockTotal <= 5
                        ? "Low stock"
                        : "Available"}
                  </Badge>
                </div>
              </div>
              {product.variants.map((variant) => {
                const available = variantAvailable(variant);
                const max = Math.max(
                  0,
                  Math.min(
                    available,
                    product.max_per_order ?? product.max_per_buyer ?? available,
                  ),
                );
                return (
                  <div
                    key={variant.id}
                    className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"
                  >
                    <div className="space-y-0.5">
                      <p className="text-sm font-semibold text-foreground">
                        {variant.label || "Standard"}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {formatNgn(variant.effective_price)}
                        {available > 0 ? ` · ${available} left` : " · Sold out"}
                      </p>
                    </div>
                    <Input
                      label="Qty"
                      hint={
                        product.max_per_order
                          ? `Max ${product.max_per_order} per order`
                          : `Max ${max}`
                      }
                      type="number"
                      min={0}
                      max={max}
                      disabled={!unlocked || max <= 0}
                      className="w-28"
                      value={String(quantities[variant.id] ?? 0)}
                      onChange={(e) => {
                        const raw = Number(e.target.value);
                        const next = Number.isFinite(raw)
                          ? Math.max(0, Math.min(max, Math.floor(raw)))
                          : 0;
                        onQuantityChange(variant.id, next);
                      }}
                    />
                  </div>
                );
              })}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
