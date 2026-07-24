"use client";

import { cn } from "@/lib/cn";
import { inferMerchTypeMark, merchPlaceholderStyle } from "@/lib/merch-fallback";

type Props = {
  productType?: string | null;
  productName?: string | null;
  eventTitle?: string | null;
  category?: string | null;
  className?: string;
  compact?: boolean;
};

/** Premium image substitute when a product has no photo. */
export function MerchFallbackVisual({
  productType,
  productName,
  eventTitle,
  category,
  className,
  compact = false,
}: Props) {
  const mark = inferMerchTypeMark({
    product_type: productType,
    name: productName,
  });
  const gradientStyle = merchPlaceholderStyle({
    product_type: productType,
    name: productName,
    category,
  });

  return (
    <div
      className={cn(
        "relative flex h-full w-full flex-col justify-between overflow-hidden",
        className,
      )}
      style={gradientStyle}
      aria-hidden
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.12]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(-35deg, var(--border) 0 1px, transparent 1px 14px)",
        }}
      />
      <div className={cn("relative z-[1]", compact ? "p-3" : "p-4 sm:p-5")}>
        <p className="text-[10px] font-extrabold tracking-[0.16em] text-muted-foreground">
          Pàdéyá
        </p>
        {eventTitle ? (
          <p
            className={cn(
              "mt-1 line-clamp-2 font-extrabold tracking-tight text-foreground",
              compact ? "text-xs" : "text-sm",
            )}
          >
            {eventTitle}
          </p>
        ) : null}
      </div>
      <div
        className={cn(
          "relative z-[1] flex items-end justify-between gap-2",
          compact ? "p-3 pt-0" : "p-4 pt-0 sm:p-5",
        )}
      >
        <span
          className={cn(
            "font-extrabold tracking-tight text-foreground",
            compact ? "text-2xl" : "text-3xl sm:text-4xl",
          )}
        >
          {mark}
        </span>
        {productName && !compact ? (
          <span className="max-w-[45%] line-clamp-2 text-right text-[11px] font-bold leading-snug text-muted-foreground">
            {productName}
          </span>
        ) : null}
      </div>
    </div>
  );
}
