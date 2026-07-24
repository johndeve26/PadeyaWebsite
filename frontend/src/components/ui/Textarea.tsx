import { type TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/cn";
import {
  fieldControlClass,
  fieldErrorClass,
  fieldHintClass,
  fieldLabelClass,
} from "@/lib/ui/field";

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
  hint?: string;
  error?: string;
};

export function Textarea({
  label,
  hint,
  error,
  id,
  className = "",
  ...props
}: TextareaProps) {
  const inputId = id ?? props.name;

  return (
    <label className="flex w-full flex-col gap-1.5 text-sm" htmlFor={inputId}>
      {label ? <span className={fieldLabelClass}>{label}</span> : null}
      <textarea
        id={inputId}
        className={fieldControlClass({
          error: Boolean(error),
          className: cn("min-h-[120px] resize-y px-3.5 py-3", className),
        })}
        aria-invalid={error ? true : undefined}
        {...props}
      />
      {error ? (
        <span className={fieldErrorClass}>{error}</span>
      ) : hint ? (
        <span className={fieldHintClass}>{hint}</span>
      ) : null}
    </label>
  );
}
