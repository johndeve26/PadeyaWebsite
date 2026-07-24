import { type InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";
import {
  authFieldOnDarkControlClass,
  authFieldOnDarkHintClass,
  authFieldOnDarkLabelClass,
} from "@/lib/ui/auth-field-on-dark";
import {
  fieldControlClass,
  fieldErrorClass,
  fieldHintClass,
  fieldLabelClass,
} from "@/lib/ui/field";

export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
  error?: string;
  /** Labels/inputs tuned for dark glass auth cards. */
  surface?: "default" | "onDark";
};

export function Input({
  label,
  hint,
  error,
  id,
  className = "",
  surface = "default",
  ...props
}: InputProps) {
  const inputId = id ?? props.name;
  const onDark = surface === "onDark";

  return (
    <label className="flex w-full flex-col gap-1.5 text-sm" htmlFor={inputId}>
      {label ? (
        <span
          className={
            onDark ? authFieldOnDarkLabelClass : fieldLabelClass
          }
        >
          {label}
        </span>
      ) : null}
      <input
        id={inputId}
        className={fieldControlClass({
          error: Boolean(error),
          className: cn(
            "h-11 px-3.5",
            onDark && authFieldOnDarkControlClass,
            className,
          ),
        })}
        aria-invalid={error ? true : undefined}
        {...props}
      />
      {error ? (
        <span className={fieldErrorClass}>{error}</span>
      ) : hint ? (
        <span className={onDark ? authFieldOnDarkHintClass : fieldHintClass}>
          {hint}
        </span>
      ) : null}
    </label>
  );
}
