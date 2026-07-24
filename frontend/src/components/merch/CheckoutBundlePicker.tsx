"use client";

import { Badge, Input } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import type { MerchBundle } from "@/lib/types/merch";

type Props = {
  bundles: MerchBundle[];
  quantities: Record<string, number>;
  onQuantityChange: (bundleId: string, quantity: number) => void;
};

function packCap(bundle: MerchBundle): number {
  const available =
    bundle.available_packs == null
      ? Number.POSITIVE_INFINITY
      : Math.max(0, Number(bundle.available_packs));
  const perBuyer =
    bundle.max_per_buyer == null
      ? Number.POSITIVE_INFINITY
      : Math.max(0, Number(bundle.max_per_buyer));
  const max = Math.min(available, perBuyer);
  return Number.isFinite(max) ? max : 99;
}

export function CheckoutBundlePicker({
  bundles,
  quantities,
  onQuantityChange,
}: Props) {
  if (bundles.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h3 className="text-lg font-extrabold tracking-tight text-foreground">
          Ticket + merch bundles
        </h3>
        <p className="text-sm text-muted-foreground">
          Packaged deals priced as one — ticket and merch issue only after payment
          confirms.
        </p>
      </div>

      <ul className="space-y-4">
        {bundles.map((bundle) => {
          const savings = Number(bundle.savings || 0);
          const max = packCap(bundle);
          const soldOut = max <= 0;
          const components = [
            bundle.ticket_type_name
              ? `1 × ${bundle.ticket_type_name}`
              : "1 × ticket",
            ...(bundle.merch_variant_rules || []).map((rule) => {
              const label = rule.variant_label
                ? `${rule.product_name || "Merch"} (${rule.variant_label})`
                : rule.product_name || "Merch";
              return `${rule.quantity} × ${label}`;
            }),
          ];
          return (
            <li
              key={bundle.id}
              className="space-y-3 border-b border-border pb-4 last:border-0 last:pb-0"
            >
              <div className="space-y-1">
                <p className="font-bold text-foreground">{bundle.name}</p>
                {bundle.description ? (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {bundle.description}
                  </p>
                ) : null}
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Includes {components.join(" · ")}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  <Badge tone="outline" size="sm">
                    {formatNgn(bundle.bundle_price)}
                  </Badge>
                  {savings > 0 ? (
                    <Badge tone="success" size="sm">
                      Save {formatNgn(savings)}
                    </Badge>
                  ) : null}
                  <Badge
                    tone={soldOut ? "danger" : max <= 5 ? "warning" : "success"}
                    size="sm"
                  >
                    {soldOut
                      ? "Sold out"
                      : bundle.available_packs == null
                        ? "Available"
                        : `${bundle.available_packs} packs left`}
                  </Badge>
                </div>
              </div>
              <Input
                label="Qty"
                hint={
                  bundle.max_per_buyer
                    ? `Max ${bundle.max_per_buyer} per buyer`
                    : undefined
                }
                type="number"
                min={0}
                max={Math.max(0, max)}
                className="w-28"
                disabled={soldOut}
                value={String(quantities[bundle.id] ?? 0)}
                onChange={(e) => {
                  const next = Math.max(
                    0,
                    Math.min(max, Number(e.target.value) || 0),
                  );
                  onQuantityChange(bundle.id, next);
                }}
              />
            </li>
          );
        })}
      </ul>
    </div>
  );
}
