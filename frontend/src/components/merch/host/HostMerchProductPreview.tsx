"use client";

import { MerchFallbackVisual } from "@/components/merch/MerchFallbackVisual";
import { Badge, Button } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import { MERCH_PRODUCT_TYPES } from "@/lib/merch-product-types";

import {
  variantEffectivePrice,
  variantSummary,
  type MerchProductFormValues,
} from "./form/types";

type Props = {
  values: MerchProductFormValues;
  eventTitle?: string | null;
};

export function HostMerchProductPreview({ values, eventTitle }: Props) {
  const summary = variantSummary(values);
  const image =
    values.use_fallback_visual || !values.cover_image_url.trim()
      ? ""
      : values.cover_image_url.trim();
  const stock = summary.totalStock;
  const stockTone =
    stock <= 0 ? "danger" : stock <= 5 ? "warning" : "success";
  const stockLabel =
    stock <= 0 ? "Sold out" : stock <= 5 ? "Low stock" : "Available";
  const locked = values.is_vault_exclusive || values.requires_ticket;
  const cta = locked
    ? values.is_vault_exclusive
      ? "How to unlock"
      : "Get eligible"
    : stock <= 0
      ? "Sold out"
      : values.variants.length > 1
        ? "Choose options"
        : "Add to cart";

  return (
    <div className="space-y-4 rounded-[var(--radius-lg)] border border-border bg-card p-4 shadow-sm">
      <p className="text-xs font-extrabold uppercase tracking-[0.12em] text-muted-foreground">
        Live public preview
      </p>

      <article className="overflow-hidden rounded-[var(--radius-md)] border border-border">
        <div className="aspect-[4/3] w-full overflow-hidden bg-surface-muted">
          {image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={image} alt="" className="h-full w-full object-cover" />
          ) : (
            <MerchFallbackVisual
              productType={values.product_type}
              productName={values.name}
              eventTitle={eventTitle}
            />
          )}
        </div>
        <div className="space-y-3 p-4">
          <div className="space-y-1">
            <h3 className="text-base font-extrabold tracking-tight text-foreground">
              {values.name.trim() || "Product name"}
            </h3>
            <p className="line-clamp-2 text-sm text-muted-foreground">
              {values.short_description.trim() ||
                values.description.trim() ||
                "Short description appears here."}
            </p>
          </div>
          <p className="text-base font-extrabold text-foreground">
            {formatNgn(summary.lowestPrice)}
            {summary.totalVariants > 1 ? (
              <span className="ml-1 text-xs font-bold text-muted-foreground">
                from
              </span>
            ) : null}
          </p>
          <div className="flex flex-wrap gap-1.5">
            <Badge tone={stockTone} size="sm">
              {stockLabel}
            </Badge>
            {values.pickup_enabled ? (
              <Badge tone="outline" size="sm">
                Pickup at event
              </Badge>
            ) : null}
            {values.shipping_enabled ? (
              <Badge tone="outline" size="sm">
                Ships
              </Badge>
            ) : null}
            {values.is_vault_exclusive ? (
              <Badge tone="accent" size="sm">
                Vault exclusive
              </Badge>
            ) : null}
            {values.requires_ticket ? (
              <Badge tone="warning" size="sm">
                Requires ticket
              </Badge>
            ) : null}
            {values.is_sponsor_branded ? (
              <Badge tone="accent" size="sm">
                Sponsor-branded
              </Badge>
            ) : null}
            {values.storefront_visibility === "post_event_drop" ? (
              <Badge tone="outline" size="sm">
                Post-event drop
              </Badge>
            ) : null}
          </div>
          <p className="text-xs text-muted-foreground">
            {summary.totalVariants} variant
            {summary.totalVariants === 1 ? "" : "s"}
            {stock > 0 ? ` · ${stock} left` : ""}
          </p>
          <Button size="sm" className="w-full" disabled={stock <= 0 && !locked}>
            {cta}
          </Button>
        </div>
      </article>

      <dl className="space-y-1 text-xs text-muted-foreground">
        <div className="flex justify-between gap-2">
          <dt>Type</dt>
          <dd className="font-bold text-foreground">
            {MERCH_PRODUCT_TYPES.find((t) => t.value === values.product_type)
              ?.label || values.product_type}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt>Status</dt>
          <dd className="font-bold capitalize text-foreground">
            {values.status}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt>From price</dt>
          <dd className="font-bold text-foreground">
            {formatNgn(
              variantEffectivePrice(
                values.base_price,
                values.variants[0] ?? {
                  key: "x",
                  label: "",
                  size: "",
                  color: "",
                  option_1_name: "",
                  option_1_value: "",
                  option_2_name: "",
                  option_2_value: "",
                  sku: "",
                  price_override: "",
                  inventory: "0",
                  status: "active",
                  print_on_demand_variant_ref: "",
                },
              ),
            )}
          </dd>
        </div>
      </dl>
    </div>
  );
}
