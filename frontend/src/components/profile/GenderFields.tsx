"use client";

import { cn } from "@/lib/cn";
import {
  DEFAULT_GENDER_VISIBILITY,
  GENDER_LABELS,
  GENDER_OPTIONS,
  GENDER_VISIBILITY_HINTS,
  GENDER_VISIBILITY_LABELS,
  GENDER_VISIBILITY_OPTIONS,
  type Gender,
  type GenderVisibility,
} from "@/lib/gender";

export type GenderFieldsProps = {
  gender: Gender | null;
  onGenderChange: (value: Gender) => void;
  genderVisibility?: GenderVisibility;
  onVisibilityChange?: (value: GenderVisibility) => void;
  /** When false (e.g. signup), only gender options are shown. */
  showVisibility?: boolean;
  required?: boolean;
  disabled?: boolean;
  surface?: "default" | "onDark";
  className?: string;
  genderName?: string;
  visibilityName?: string;
};

/**
 * Settings / signup gender radios. No default gender selection —
 * callers must start with `gender: null` until the user chooses.
 */
export function GenderFields({
  gender,
  onGenderChange,
  genderVisibility = DEFAULT_GENDER_VISIBILITY,
  onVisibilityChange,
  showVisibility = true,
  required = false,
  disabled = false,
  surface = "default",
  className = "",
  genderName = "gender",
  visibilityName = "gender_visibility",
}: GenderFieldsProps) {
  const onDark = surface === "onDark";

  return (
    <div className={cn("space-y-4", className)}>
      <fieldset disabled={disabled} className="space-y-2 disabled:opacity-70">
        <legend
          className={cn(
            "text-sm font-semibold",
            onDark ? "text-paper" : "text-foreground",
          )}
        >
          Gender
          {required ? (
            <span className="text-danger" aria-hidden>
              {" "}
              *
            </span>
          ) : null}
        </legend>
        <p
          className={cn(
            "text-xs leading-relaxed",
            onDark ? "text-paper/70" : "text-muted-foreground",
          )}
        >
          Choose how you identify. You can change this later in settings.
        </p>
        <div
          className="grid gap-2 sm:grid-cols-3"
          role="radiogroup"
          aria-required={required || undefined}
          aria-label="Gender"
        >
          {GENDER_OPTIONS.map((option) => {
            const selected = gender === option;
            return (
              <label
                key={option}
                className={cn(
                  "flex cursor-pointer flex-col gap-1 rounded-[var(--radius-lg)] border p-3 transition-colors",
                  selected
                    ? onDark
                      ? "border-primary bg-primary/15 ring-1 ring-primary/40"
                      : "border-primary bg-primary/5 ring-1 ring-primary/30"
                    : onDark
                      ? "border-paper/25 bg-black/30 hover:border-paper/45"
                      : "border-border bg-card/50 hover:border-border-strong dark:bg-surface-elevated/50",
                )}
              >
                <span className="flex items-center gap-2">
                  <input
                    type="radio"
                    name={genderName}
                    value={option}
                    checked={selected}
                    required={required}
                    disabled={disabled}
                    onChange={() => onGenderChange(option)}
                    className="mt-0.5"
                  />
                  <span
                    className={cn(
                      "text-sm font-semibold",
                      onDark ? "text-paper" : "text-foreground",
                    )}
                  >
                    {GENDER_LABELS[option]}
                  </span>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {showVisibility && onVisibilityChange ? (
        <fieldset disabled={disabled} className="space-y-2 disabled:opacity-70">
          <legend
            className={cn(
              "text-sm font-semibold",
              onDark ? "text-paper" : "text-foreground",
            )}
          >
            Who can see your gender
          </legend>
          <p
            className={cn(
              "text-xs leading-relaxed",
              onDark ? "text-paper/70" : "text-muted-foreground",
            )}
          >
            Gender visibility controls where M/F can appear. Prefer not to say
            never shows a badge.
          </p>
          <div
            className="grid gap-2"
            role="radiogroup"
            aria-label="Gender visibility"
          >
            {GENDER_VISIBILITY_OPTIONS.map((option) => {
              const selected = genderVisibility === option;
              return (
                <label
                  key={option}
                  className={cn(
                    "flex cursor-pointer flex-col gap-1 rounded-[var(--radius-lg)] border p-3 transition-colors",
                    selected
                      ? onDark
                        ? "border-primary bg-primary/15 ring-1 ring-primary/40"
                        : "border-primary bg-primary/5 ring-1 ring-primary/30"
                      : onDark
                        ? "border-paper/25 bg-black/30 hover:border-paper/45"
                        : "border-border bg-card/50 hover:border-border-strong dark:bg-surface-elevated/50",
                  )}
                >
                  <span className="flex items-start gap-2">
                    <input
                      type="radio"
                      name={visibilityName}
                      value={option}
                      checked={selected}
                      disabled={disabled}
                      onChange={() => onVisibilityChange(option)}
                      className="mt-1"
                    />
                    <span className="min-w-0">
                      <span
                        className={cn(
                          "block text-sm font-semibold",
                          onDark ? "text-paper" : "text-foreground",
                        )}
                      >
                        {GENDER_VISIBILITY_LABELS[option]}
                      </span>
                      <span
                        className={cn(
                          "mt-0.5 block text-xs leading-relaxed",
                          onDark ? "text-paper/65" : "text-muted-foreground",
                        )}
                      >
                        {GENDER_VISIBILITY_HINTS[option]}
                      </span>
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>
      ) : null}
    </div>
  );
}
