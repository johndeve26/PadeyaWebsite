"use client";

import { BrandAccentField } from "@/components/events/studio/BrandAccentField";
import { Button, Input } from "@/components/ui";
import { formatNgn } from "@/lib/format";

import {
  createDefaultVariant,
  newVariantKey,
  variantSummary,
  type MerchProductFormValues,
  type MerchVariantFormRow,
} from "./types";

type Props = {
  values: MerchProductFormValues;
  onChange: (variants: MerchVariantFormRow[]) => void;
  onBasePriceChange: (value: string) => void;
  fieldErrors?: Record<string, string>;
};

function updateVariant(
  variants: MerchVariantFormRow[],
  key: string,
  patch: Partial<MerchVariantFormRow>,
): MerchVariantFormRow[] {
  return variants.map((v) => (v.key === key ? { ...v, ...patch } : v));
}

export function MerchVariantsEditor({
  values,
  onChange,
  onBasePriceChange,
  fieldErrors = {},
}: Props) {
  const summary = variantSummary(values);

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          label="Base price (₦)"
          type="number"
          min={0}
          value={values.base_price}
          onChange={(e) => onBasePriceChange(e.target.value)}
          error={fieldErrors.base_price}
        />
        <label className="block space-y-1.5 text-sm">
          <span className="font-bold text-foreground">Currency</span>
          <select
            className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
            value={values.currency}
            disabled
          >
            <option value="NGN">NGN</option>
          </select>
        </label>
      </div>

      <div className="grid grid-cols-2 gap-3 rounded-[var(--radius-md)] border border-border bg-surface-muted/50 p-3 sm:grid-cols-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
            Variants
          </p>
          <p className="text-base font-extrabold text-foreground">
            {summary.totalVariants}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
            Total stock
          </p>
          <p className="text-base font-extrabold text-foreground">
            {summary.totalStock}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
            Lowest
          </p>
          <p className="text-base font-extrabold text-foreground">
            {formatNgn(summary.lowestPrice)}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
            Highest
          </p>
          <p className="text-base font-extrabold text-foreground">
            {formatNgn(summary.highestPrice)}
          </p>
        </div>
      </div>

      {fieldErrors.variants ? (
        <p className="text-sm font-medium text-danger">{fieldErrors.variants}</p>
      ) : null}

      <ul className="space-y-4">
        {values.variants.map((variant, index) => (
          <li
            key={variant.key}
            className="space-y-3 rounded-[var(--radius-lg)] border border-border bg-card p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-extrabold text-foreground">
                Variant {index + 1}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    onChange([
                      ...values.variants,
                      {
                        ...variant,
                        key: newVariantKey(),
                        id: undefined,
                        label: `${variant.label || "Variant"} copy`,
                        sku: "",
                      },
                    ])
                  }
                >
                  Duplicate
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={values.variants.length <= 1}
                  onClick={() =>
                    onChange(values.variants.filter((v) => v.key !== variant.key))
                  }
                >
                  Remove
                </Button>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Input
                label="Variant name"
                value={variant.label}
                onChange={(e) =>
                  onChange(
                    updateVariant(values.variants, variant.key, {
                      label: e.target.value,
                    }),
                  )
                }
                placeholder="One size"
              />
              <Input
                label="Size"
                value={variant.size}
                onChange={(e) =>
                  onChange(
                    updateVariant(values.variants, variant.key, {
                      size: e.target.value,
                    }),
                  )
                }
                placeholder="L"
              />
              <div className="sm:col-span-2 lg:col-span-1">
                <BrandAccentField
                  optional
                  label="Color"
                  value={variant.color}
                  onChange={(color) =>
                    onChange(
                      updateVariant(values.variants, variant.key, {
                        color,
                      }),
                    )
                  }
                />
              </div>
              <Input
                label="SKU"
                value={variant.sku}
                onChange={(e) =>
                  onChange(
                    updateVariant(values.variants, variant.key, {
                      sku: e.target.value,
                    }),
                  )
                }
              />
              <Input
                label="Price override"
                type="number"
                min={0}
                value={variant.price_override}
                onChange={(e) =>
                  onChange(
                    updateVariant(values.variants, variant.key, {
                      price_override: e.target.value,
                    }),
                  )
                }
                placeholder="Optional"
              />
              <Input
                label="Inventory"
                type="number"
                min={0}
                value={variant.inventory}
                onChange={(e) =>
                  onChange(
                    updateVariant(values.variants, variant.key, {
                      inventory: e.target.value,
                    }),
                  )
                }
                error={fieldErrors[`variant_${variant.key}_inventory`]}
              />
              <Input
                label="Option 1 name"
                value={variant.option_1_name}
                onChange={(e) =>
                  onChange(
                    updateVariant(values.variants, variant.key, {
                      option_1_name: e.target.value,
                    }),
                  )
                }
                placeholder="Fit"
              />
              <Input
                label="Option 1 value"
                value={variant.option_1_value}
                onChange={(e) =>
                  onChange(
                    updateVariant(values.variants, variant.key, {
                      option_1_value: e.target.value,
                    }),
                  )
                }
                placeholder="Relaxed"
              />
              <Input
                label="Option 2 name"
                value={variant.option_2_name}
                onChange={(e) =>
                  onChange(
                    updateVariant(values.variants, variant.key, {
                      option_2_name: e.target.value,
                    }),
                  )
                }
              />
              <Input
                label="Option 2 value"
                value={variant.option_2_value}
                onChange={(e) =>
                  onChange(
                    updateVariant(values.variants, variant.key, {
                      option_2_value: e.target.value,
                    }),
                  )
                }
              />
              <label className="block space-y-1.5 text-sm">
                <span className="font-bold text-foreground">Status</span>
                <select
                  className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
                  value={variant.status}
                  onChange={(e) =>
                    onChange(
                      updateVariant(values.variants, variant.key, {
                        status: e.target.value,
                      }),
                    )
                  }
                >
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                  <option value="sold_out">Sold out</option>
                </select>
              </label>
            </div>
          </li>
        ))}
      </ul>

      <Button
        type="button"
        variant="secondary"
        onClick={() =>
          onChange([
            ...values.variants,
            createDefaultVariant({ label: `Variant ${values.variants.length + 1}` }),
          ])
        }
      >
        Add variant
      </Button>
    </div>
  );
}
