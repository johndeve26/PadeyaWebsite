"use client";

import { useState } from "react";

import { cn } from "@/lib/cn";
import { fieldControlClass } from "@/lib/ui/field";

type Props = {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  disabled?: boolean;
  className?: string;
  id?: string;
  "aria-label"?: string;
};

const stepperButtonClass =
  "flex min-w-11 items-center justify-center border-border bg-input-background px-3 text-lg font-bold leading-none text-foreground transition-colors hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-40";

export function QuantityInput({
  value,
  onChange,
  min = 1,
  max = 99,
  disabled = false,
  className = "",
  id,
  "aria-label": ariaLabel = "Quantity",
}: Props) {
  const [draft, setDraft] = useState(String(value));
  // Reset the draft during render when the incoming value changes externally
  // (e.g. stock clamping) — avoids a setState-in-effect cascading render.
  const [prevValue, setPrevValue] = useState(value);
  if (value !== prevValue) {
    setPrevValue(value);
    setDraft(String(value));
  }

  function commit(raw: string) {
    const parsed = Number.parseInt(raw, 10);
    const next = Number.isFinite(parsed)
      ? Math.min(max, Math.max(min, parsed))
      : min;
    onChange(next);
    setDraft(String(next));
  }

  function step(delta: number) {
    const next = Math.min(max, Math.max(min, value + delta));
    onChange(next);
    setDraft(String(next));
  }

  return (
    <div
      className={cn(
        "inline-flex h-11 items-stretch overflow-hidden rounded-[var(--radius-md)] border border-input-border bg-input-background shadow-[var(--shadow-soft)]",
        disabled && "opacity-80",
        className,
      )}
    >
      <button
        type="button"
        aria-label="Decrease quantity"
        disabled={disabled || value <= min}
        onClick={() => step(-1)}
        className={cn(stepperButtonClass, "border-r")}
      >
        −
      </button>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        aria-label={ariaLabel}
        disabled={disabled}
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value.replace(/\D/g, ""));
        }}
        onBlur={() => commit(draft)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.currentTarget.blur();
          }
        }}
        className={fieldControlClass({
          className:
            "h-full w-12 min-w-12 border-0 bg-transparent px-1 text-center text-sm font-semibold shadow-none focus:ring-0 focus:ring-offset-0",
        })}
      />
      <button
        type="button"
        aria-label="Increase quantity"
        disabled={disabled || value >= max}
        onClick={() => step(1)}
        className={cn(stepperButtonClass, "border-l")}
      >
        +
      </button>
    </div>
  );
}
