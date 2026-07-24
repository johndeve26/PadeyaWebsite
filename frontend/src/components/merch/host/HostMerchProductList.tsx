"use client";

import Link from "next/link";

import {
  Badge,
  Button,
  ConfirmAction,
  EmptyState,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import {
  archiveMerchProduct,
  duplicateMerchProduct,
  pauseMerchProduct,
  updateMerchProduct,
} from "@/lib/merch-api";
import { MERCH_PRODUCT_TYPES } from "@/lib/merch-product-types";
import type { MerchProduct } from "@/lib/types/merch";

const LOW_STOCK_THRESHOLD = 5;

function typeLabel(value?: string | null): string {
  if (!value) return "—";
  return MERCH_PRODUCT_TYPES.find((t) => t.value === value)?.label ?? value;
}

function priceRange(product: MerchProduct): string {
  const min = Number(product.price_min ?? product.base_price);
  const max = Number(product.price_max ?? product.base_price);
  if (!Number.isFinite(min)) return formatNgn(product.base_price);
  if (min === max) return formatNgn(min);
  return `${formatNgn(min)} – ${formatNgn(max)}`;
}

function hostStockBadge(
  product: MerchProduct,
): "sold_out" | "low_stock" | null {
  const variants = (product.variants ?? []).filter(
    (v) => v.status !== "archived",
  );
  if (variants.length === 0) {
    const total = product.total_inventory ?? 0;
    if (total <= 0) return "sold_out";
    if (total <= LOW_STOCK_THRESHOLD) return "low_stock";
    return null;
  }
  let available = 0;
  let anyLow = false;
  for (const v of variants) {
    const qty =
      v.available_quantity ??
      Math.max(0, (v.inventory_count ?? 0) - (v.reserved_quantity ?? 0));
    available += qty;
    if (qty > 0 && qty <= LOW_STOCK_THRESHOLD) anyLow = true;
  }
  if (available <= 0) return "sold_out";
  if (anyLow || available <= LOW_STOCK_THRESHOLD) return "low_stock";
  return null;
}

export function HostMerchProductList({
  products,
  editHref,
  showEvent = false,
  onChanged,
}: {
  products: MerchProduct[];
  editHref: (product: MerchProduct) => string;
  showEvent?: boolean;
  onChanged: () => void | Promise<void>;
}) {
  const toast = useToast();

  if (products.length === 0) {
    return (
      <EmptyState
        title="No merch yet"
        description="Add a product with at least one size/color variant and inventory. Choose pickup and/or delivery per product."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[880px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs font-bold uppercase tracking-wide text-muted-foreground">
            <th className="py-3 pr-3 font-bold">Product</th>
            <th className="py-3 pr-3 font-bold">Type</th>
            <th className="py-3 pr-3 font-bold">Price</th>
            <th className="py-3 pr-3 font-bold">Variants</th>
            <th className="py-3 pr-3 font-bold">Stock</th>
            <th className="py-3 pr-3 font-bold">Sold</th>
            <th className="py-3 pr-3 font-bold">Status</th>
            <th className="py-3 font-bold">Actions</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => {
            const image = product.cover_image_url || product.image_url;
            const stockBadge = hostStockBadge(product);
            return (
              <tr
                key={product.id}
                className="border-b border-border/80 align-top last:border-0"
              >
                <td className="py-4 pr-3">
                  <div className="flex gap-3">
                    <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-[var(--radius-sm)] bg-surface-muted">
                      {image ? (
                        // Host-provided cover URLs — not optimized CDN assets.
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={image}
                          alt=""
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <span className="flex h-full items-center justify-center text-[10px] font-bold uppercase text-muted-foreground">
                          Merch
                        </span>
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-bold text-foreground">
                          {product.name}
                        </p>
                        {stockBadge === "sold_out" ? (
                          <Badge tone="danger" size="sm">
                            Sold out
                          </Badge>
                        ) : null}
                        {stockBadge === "low_stock" ? (
                          <Badge tone="warning" size="sm">
                            Low stock
                          </Badge>
                        ) : null}
                      </div>
                      {showEvent && product.event_title ? (
                        <p className="text-xs text-muted-foreground">
                          {product.event_title}
                        </p>
                      ) : null}
                      {product.short_description ? (
                        <p className="line-clamp-1 text-xs text-muted-foreground">
                          {product.short_description}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </td>
                <td className="py-4 pr-3 text-muted-foreground">
                  {typeLabel(product.product_type)}
                </td>
                <td className="py-4 pr-3 font-medium text-foreground">
                  {priceRange(product)}
                </td>
                <td className="py-4 pr-3 text-muted-foreground">
                  {product.variant_count ?? product.variants.length}
                </td>
                <td className="py-4 pr-3 text-muted-foreground">
                  {product.total_inventory ?? 0}
                </td>
                <td className="py-4 pr-3 text-muted-foreground">
                  {product.sold_count ?? 0}
                </td>
                <td className="py-4 pr-3">
                  <div className="flex flex-col gap-1.5">
                    <StatusBadge status={product.status} />
                    {product.moderation_status &&
                    product.moderation_status !== "clear" ? (
                      <>
                        <StatusBadge status={product.moderation_status} />
                        {product.moderation_note ? (
                          <p className="max-w-[12rem] text-xs text-muted-foreground">
                            {product.moderation_note}
                          </p>
                        ) : null}
                      </>
                    ) : null}
                  </div>
                </td>
                <td className="py-4">
                  <div className="flex flex-wrap gap-1.5">
                    <Link href={editHref(product)}>
                      <Button size="sm" variant="secondary">
                        Edit
                      </Button>
                    </Link>
                    {product.status === "active" ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() =>
                          void (
                            product.event_id
                              ? pauseMerchProduct(product.id, product.event_id)
                              : updateMerchProduct(product.id, {
                                  status: "paused",
                                })
                          )
                            .then(() => onChanged())
                            .catch((err) =>
                              toast.push({
                                tone: "danger",
                                title:
                                  err instanceof ApiError
                                    ? err.detail
                                    : "Could not pause",
                              }),
                            )
                        }
                      >
                        Pause
                      </Button>
                    ) : product.status !== "archived" &&
                      product.moderation_status !== "hidden" &&
                      product.moderation_status !== "removed" ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() =>
                          void updateMerchProduct(product.id, {
                            status: "active",
                          })
                            .then(() => onChanged())
                            .catch((err) =>
                              toast.push({
                                tone: "danger",
                                title:
                                  err instanceof ApiError
                                    ? err.detail
                                    : "Could not activate",
                              }),
                            )
                        }
                      >
                        Activate
                      </Button>
                    ) : null}
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        void duplicateMerchProduct(product.id)
                          .then(async () => {
                            toast.push({
                              tone: "success",
                              title: "Product duplicated as draft",
                            });
                            await onChanged();
                          })
                          .catch((err) =>
                            toast.push({
                              tone: "danger",
                              title:
                                err instanceof ApiError
                                  ? err.detail
                                  : "Could not duplicate",
                            }),
                          )
                      }
                    >
                      Duplicate
                    </Button>
                    <ConfirmAction
                      label="Archive"
                      title="Archive product?"
                      description="Archived merch is hidden from buyers. Existing pickups stay."
                      confirmLabel="Archive"
                      variant="ghost"
                      onConfirm={async () => {
                        try {
                          await archiveMerchProduct(product.id);
                          toast.push({
                            tone: "success",
                            title: "Product archived",
                          });
                          await onChanged();
                        } catch (err) {
                          toast.push({
                            tone: "danger",
                            title:
                              err instanceof ApiError
                                ? err.detail
                                : "Could not archive",
                          });
                        }
                      }}
                    />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
