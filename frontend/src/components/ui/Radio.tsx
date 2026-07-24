import { type InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";
import { fieldChoiceClass, fieldHintClass, fieldLabelClass } from "@/lib/ui/field";

export type RadioProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label?: string;
  hint?: string;
};

export function Radio({
  label,
  hint,
  id,
  className = "",
  ...props
}: RadioProps) {
  const inputId = id ?? (props.name && props.value ? `${props.name}-${props.value}` : undefined);

  return (
    <div className="flex flex-col gap-1">
      <label
        htmlFor={inputId}
        className="inline-flex cursor-pointer items-start gap-2.5 text-sm text-foreground"
      >
        <input
          id={inputId}
          type="radio"
          className={cn(fieldChoiceClass, "mt-0.5 rounded-full", className)}
          {...props}
        />
        {label ? (
          <span className={cn(fieldLabelClass, "normal-case tracking-normal")}>
            {label}
          </span>
        ) : null}
      </label>
      {hint ? <span className={cn(fieldHintClass, "pl-6")}>{hint}</span> : null}
    </div>
  );
}
