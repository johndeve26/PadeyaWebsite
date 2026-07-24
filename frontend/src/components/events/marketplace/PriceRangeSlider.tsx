"use client";

import { cn } from "@/lib/cn";
import { formatNgn } from "@/lib/format";
import { fieldHintClass, fieldLabelClass } from "@/lib/ui/field";

export function PriceRangeSlider({
  min = 0,
  max,
  valueMin,
  valueMax,
  step = 50,
  onChange,
  label = "Price",
  className = "",
  id = "price-range",
}: {
  min?: number;
  max: number;
  valueMin: number;
  valueMax: number;
  step?: number;
  onChange: (next: { priceMin: number; priceMax: number }) => void;
  label?: string;
  className?: string;
  id?: string;
}) {
  const boundMin = Math.min(min, max);
  const boundMax = Math.max(min, max);
  const lo = Math.min(Math.max(valueMin, boundMin), boundMax);
  const hi = Math.min(Math.max(valueMax, boundMin), boundMax);
  const safeLo = Math.min(lo, hi);
  const safeHi = Math.max(lo, hi);
  const span = boundMax - boundMin || 1;
  const leftPct = ((safeLo - boundMin) / span) * 100;
  const rightPct = ((safeHi - boundMin) / span) * 100;

  function setLo(next: number) {
    const clamped = Math.min(Math.max(next, boundMin), safeHi);
    onChange({ priceMin: clamped, priceMax: safeHi });
  }

  function setHi(next: number) {
    const clamped = Math.max(Math.min(next, boundMax), safeLo);
    onChange({ priceMin: safeLo, priceMax: clamped });
  }

  return (
    <div className={cn("min-w-0 space-y-2", className)}>
      <div className="flex items-baseline justify-between gap-3">
        <span className={fieldLabelClass} id={`${id}-label`}>
          {label}
        </span>
        <span className="truncate text-xs font-semibold tabular-nums text-foreground">
          {formatNgn(safeLo)} – {formatNgn(safeHi)}
        </span>
      </div>

      <div className="relative h-8 touch-none select-none">
        <div
          aria-hidden
          className="absolute left-0 right-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-muted"
        />
        <div
          aria-hidden
          className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-primary"
          style={{
            left: `${leftPct}%`,
            right: `${100 - rightPct}%`,
          }}
        />
        <input
          id={`${id}-min`}
          type="range"
          min={boundMin}
          max={boundMax}
          step={step}
          value={safeLo}
          aria-labelledby={`${id}-label`}
          aria-label="Minimum price"
          aria-valuemin={boundMin}
          aria-valuemax={safeHi}
          aria-valuenow={safeLo}
          aria-valuetext={formatNgn(safeLo)}
          onChange={(e) => setLo(Number(e.target.value))}
          className="padeya-price-range-thumb absolute inset-0 z-[1] m-0 h-8 w-full appearance-none bg-transparent"
        />
        <input
          id={`${id}-max`}
          type="range"
          min={boundMin}
          max={boundMax}
          step={step}
          value={safeHi}
          aria-labelledby={`${id}-label`}
          aria-label="Maximum price"
          aria-valuemin={safeLo}
          aria-valuemax={boundMax}
          aria-valuenow={safeHi}
          aria-valuetext={formatNgn(safeHi)}
          onChange={(e) => setHi(Number(e.target.value))}
          className="padeya-price-range-thumb absolute inset-0 z-[2] m-0 h-8 w-full appearance-none bg-transparent"
        />
      </div>

      <div className={cn("flex justify-between gap-3", fieldHintClass)}>
        <span className="tabular-nums">{formatNgn(boundMin)}</span>
        <span className="tabular-nums">{formatNgn(boundMax)}</span>
      </div>
    </div>
  );
}
