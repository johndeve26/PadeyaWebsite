import { type SelectHTMLAttributes } from "react";

import { cn } from "@/lib/cn";
import {
  fieldControlClass,
  fieldErrorClass,
  fieldHintClass,
  fieldLabelClass,
} from "@/lib/ui/field";

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  hint?: string;
  error?: string;
};

export function Select({
  label,
  hint,
  error,
  id,
  className = "",
  children,
  ...props
}: SelectProps) {
  const inputId = id ?? props.name;

  return (
    <label className="flex w-full flex-col gap-1.5 text-sm" htmlFor={inputId}>
      {label ? <span className={fieldLabelClass}>{label}</span> : null}
      <span className="relative block">
        <select
          id={inputId}
          className={fieldControlClass({
            error: Boolean(error),
            className: cn(
              "h-11 appearance-none px-3.5 pr-10",
              className,
            ),
          })}
          aria-invalid={error ? true : undefined}
          {...props}
        >
          {children}
        </select>
        <span
          aria-hidden
          className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground"
        >
          ▾
        </span>
      </span>
      {error ? (
        <span className={fieldErrorClass}>{error}</span>
      ) : hint ? (
        <span className={fieldHintClass}>{hint}</span>
      ) : null}
    </label>
  );
}
