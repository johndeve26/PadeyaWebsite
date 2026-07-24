import { type InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";
import { fieldChoiceClass, fieldHintClass, fieldLabelClass } from "@/lib/ui/field";

export type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label?: string;
  hint?: string;
};

export function Checkbox({
  label,
  hint,
  id,
  className = "",
  ...props
}: CheckboxProps) {
  const inputId = id ?? props.name;

  return (
    <div className="flex flex-col gap-1">
      <label
        htmlFor={inputId}
        className="inline-flex cursor-pointer items-start gap-2.5 text-sm text-foreground"
      >
        <input
          id={inputId}
          type="checkbox"
          className={cn(fieldChoiceClass, "mt-0.5 rounded-[3px]", className)}
          {...props}
        />
        {label ? (
          <span className="min-w-0">
            <span className={cn(fieldLabelClass, "normal-case tracking-normal")}>
              {label}
            </span>
          </span>
        ) : null}
      </label>
      {hint ? <span className={cn(fieldHintClass, "pl-6")}>{hint}</span> : null}
    </div>
  );
}
