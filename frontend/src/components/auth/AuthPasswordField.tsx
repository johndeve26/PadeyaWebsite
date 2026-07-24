"use client";

import { useId, useState } from "react";

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

function EyeIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
      <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
      <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
      <line x1="2" x2="22" y1="2" y2="22" />
    </svg>
  );
}

type Props = {
  label?: string;
  hint?: string;
  error?: string;
  name?: string;
  id?: string;
  autoComplete?: string;
  required?: boolean;
  minLength?: number;
  value: string;
  onChange: (value: string) => void;
  className?: string;
  surface?: "default" | "onDark";
};

export function AuthPasswordField({
  label = "Password",
  hint,
  error,
  name = "password",
  id,
  autoComplete = "current-password",
  required,
  minLength,
  value,
  onChange,
  className,
  surface = "default",
}: Props) {
  const [visible, setVisible] = useState(false);
  const generatedId = useId();
  const inputId = id ?? name ?? generatedId;
  const onDark = surface === "onDark";

  return (
    <div className={cn("flex w-full flex-col gap-1.5 text-sm", className)}>
      <div className="flex items-center justify-between gap-2">
        {label ? (
          <label
            htmlFor={inputId}
            className={
              onDark ? authFieldOnDarkLabelClass : fieldLabelClass
            }
          >
            {label}
          </label>
        ) : null}
      </div>
      <div className="relative">
        <input
          id={inputId}
          name={name}
          type={visible ? "text" : "password"}
          autoComplete={autoComplete}
          required={required}
          minLength={minLength}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={fieldControlClass({
            error: Boolean(error),
            className: cn(
              "h-11 px-3.5 pr-11",
              onDark && authFieldOnDarkControlClass,
            ),
          })}
          aria-invalid={error ? true : undefined}
        />
        <button
          type="button"
          className={cn(
            "absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-[var(--radius-md)] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
            onDark
              ? "!text-white/55 hover:!text-white"
              : "text-muted-foreground hover:text-foreground",
          )}
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Hide password" : "Show password"}
          aria-pressed={visible}
        >
          {visible ? (
            <EyeOffIcon className="h-[1.125rem] w-[1.125rem]" />
          ) : (
            <EyeIcon className="h-[1.125rem] w-[1.125rem]" />
          )}
        </button>
      </div>
      {error ? (
        <span className={fieldErrorClass}>{error}</span>
      ) : hint ? (
        <span className={onDark ? authFieldOnDarkHintClass : fieldHintClass}>
          {hint}
        </span>
      ) : null}
    </div>
  );
}
