"use client";

import { useId, useState } from "react";

import { cn } from "@/lib/cn";
import {
  cssColorToHex,
  DEFAULT_BRAND_ACCENT,
  normalizeCssColor,
  resolveCssColor,
} from "@/lib/css-color";
import {
  fieldControlClass,
  fieldErrorClass,
  fieldHintClass,
  fieldLabelClass,
} from "@/lib/ui/field";

const DEFAULT_HINT =
  "Optional. Pick a color, or type a name/hex (blue, #8EF012). Leave blank for Pàdéyá green.";

const OPTIONAL_HINT =
  "Pick a color or type a name/hex (Black, navy, #1a1a1a). Leave blank if not needed.";

export function BrandAccentField({
  value,
  onChange,
  label = "Brand accent override",
  optional = false,
  hint,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  /** When true, blank shows a neutral swatch instead of the Pàdéyá default. */
  optional?: boolean;
  hint?: string;
  placeholder?: string;
}) {
  const inputId = useId();
  const pickerId = useId();
  const [draft, setDraft] = useState(value);
  const [prevValue, setPrevValue] = useState(value);
  const [error, setError] = useState<string | null>(null);

  // Sync draft when parent value changes (e.g. form reset) without an effect.
  if (value !== prevValue) {
    setPrevValue(value);
    setDraft(value);
  }

  const isBlank = !draft.trim();
  const previewColor = optional
    ? isBlank
      ? "var(--muted)"
      : resolveCssColor(draft, "var(--muted)")
    : resolveCssColor(draft);
  const pickerValue = cssColorToHex(
    isBlank && optional ? "#d4d4d4" : previewColor,
  );
  const hintText = hint ?? (optional ? OPTIONAL_HINT : DEFAULT_HINT);
  const placeholderText = placeholder ?? (optional ? "Black" : DEFAULT_BRAND_ACCENT);

  function commit(next: string) {
    const trimmed = next.trim();
    if (!trimmed) {
      setError(null);
      setDraft("");
      onChange("");
      return;
    }
    const normalized = normalizeCssColor(trimmed);
    if (!normalized) {
      setError("Enter a valid color name or hex (e.g. blue, #8EF012).");
      return;
    }
    setError(null);
    setDraft(normalized);
    onChange(normalized);
  }

  return (
    <div className="flex w-full flex-col gap-1.5 text-sm">
      <span className={fieldLabelClass}>{label}</span>
      <div className="flex items-center gap-2">
        <div
          className="relative h-11 w-11 shrink-0 overflow-hidden rounded-[var(--radius-md)] border border-input-border shadow-[var(--shadow-soft)]"
          title={
            isBlank
              ? optional
                ? "No color"
                : "Pàdéyá green (default)"
              : previewColor
          }
          aria-hidden
        >
          <span
            className="absolute inset-0"
            style={{ backgroundColor: previewColor }}
          />
          {isBlank && !optional ? (
            <span className="absolute inset-x-0 bottom-0 bg-ink/55 px-0.5 py-px text-center text-[8px] font-bold uppercase tracking-wide text-paper">
              Default
            </span>
          ) : null}
        </div>
        <input
          id={pickerId}
          type="color"
          value={pickerValue}
          onChange={(e) => {
            const hex = e.target.value;
            setError(null);
            setDraft(hex);
            onChange(hex);
          }}
          className={cn(
            "h-11 w-11 shrink-0 cursor-pointer rounded-[var(--radius-md)] border border-input-border bg-input-background p-1 shadow-[var(--shadow-soft)]",
            "disabled:cursor-not-allowed disabled:opacity-60",
          )}
          aria-label="Pick accent color"
        />
        <input
          id={inputId}
          type="text"
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            if (error) setError(null);
          }}
          onBlur={() => commit(draft)}
          placeholder={placeholderText}
          className={fieldControlClass({
            error: Boolean(error),
            className: "h-11 min-w-0 flex-1 px-3.5",
          })}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${inputId}-error` : `${inputId}-hint`}
        />
      </div>
      {error ? (
        <span id={`${inputId}-error`} className={fieldErrorClass}>
          {error}
        </span>
      ) : (
        <span id={`${inputId}-hint`} className={fieldHintClass}>
          {hintText}
        </span>
      )}
    </div>
  );
}
