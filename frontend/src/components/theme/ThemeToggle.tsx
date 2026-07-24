"use client";

import { useTheme } from "@/hooks/useTheme";
import { cn } from "@/lib/cn";
import {
  THEME_LABELS,
  THEME_OPTIONS,
  type ThemePreference,
} from "@/lib/theme";

function ThemeIcon({ theme }: { theme: ThemePreference }) {
  if (theme === "dark") {
    return (
      <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden fill="none">
        <path
          d="M21 14.5A8.5 8.5 0 0 1 9.5 3 7 7 0 1 0 21 14.5Z"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinejoin="round"
        />
      </svg>
    );
  }
  if (theme === "system") {
    return (
      <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden fill="none">
        <rect
          x="3.75"
          y="4.75"
          width="16.5"
          height="11.5"
          rx="1.5"
          stroke="currentColor"
          strokeWidth="1.75"
        />
        <path
          d="M8 19.25h8M12 16.25v3"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
        />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden fill="none">
      <circle cx="12" cy="12" r="3.25" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="M12 3.5v1.75M12 18.75V20.5M3.5 12h1.75M18.75 12H20.5M6.05 6.05l1.24 1.24M16.71 16.71l1.24 1.24M6.05 17.95l1.24-1.24M16.71 7.29l1.24-1.24"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background";

export function ThemeToggle({
  className = "",
  compact = false,
  variant = "button",
  showLabels = "responsive",
  tone = "default",
}: {
  className?: string;
  /** Icon-only control (navbar / topbar). */
  compact?: boolean;
  /**
   * `button` — cycles Light → Dark → System.
   * `segmented` — explicit Light / Dark / System choices (settings).
   */
  variant?: "button" | "segmented";
  /** Segmented label visibility. Settings pages should use `always`. */
  showLabels?: "always" | "responsive";
  /** `onDark` — light chrome for transparent header over dark heroes. */
  tone?: "default" | "onDark";
}) {
  const { theme, setTheme, cycleTheme, mounted } = useTheme();
  const label = THEME_LABELS[theme];

  if (variant === "segmented") {
    return (
      <div
        role="radiogroup"
        aria-label="Appearance preference"
        className={cn(
          "grid grid-cols-3 gap-1 rounded-[var(--radius-md)] border border-border bg-surface-muted p-1",
          className,
        )}
      >
        {THEME_OPTIONS.map((option) => {
          const active = mounted && theme === option;
          return (
            <button
              key={option}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => setTheme(option)}
              className={cn(
                "inline-flex h-10 items-center justify-center gap-1.5 rounded-[var(--radius-sm)] px-2 text-sm font-semibold transition-colors",
                focusRing,
                active
                  ? "bg-card text-heading shadow-[var(--shadow-soft)] ring-1 ring-border dark:bg-surface-elevated"
                  : "text-muted-foreground hover:bg-surface-inset hover:text-foreground",
              )}
            >
              <ThemeIcon theme={option} />
              {showLabels === "always" ? (
                <span>{THEME_LABELS[option]}</span>
              ) : (
                <>
                  <span className="hidden sm:inline">{THEME_LABELS[option]}</span>
                  <span className="sr-only sm:hidden">{THEME_LABELS[option]}</span>
                </>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={cycleTheme}
      aria-label={
        mounted
          ? `Color theme: ${label}. Activate to cycle Light, Dark, or System.`
          : "Color theme. Activate to change preference."
      }
      title={mounted ? `Theme: ${label}` : "Theme"}
      className={cn(
        "inline-flex h-11 items-center justify-center gap-2 rounded-[var(--radius-sm)] border text-sm font-semibold transition-colors",
        focusRing,
        compact ? "w-11 px-0" : "px-3",
        tone === "onDark"
          ? "border-paper/30 bg-transparent text-paper hover:border-paper/55 hover:bg-paper/10 focus-visible:ring-offset-ink"
          : "border-border bg-card text-foreground hover:border-border-strong/50 hover:bg-surface-muted active:bg-surface-inset dark:bg-surface-elevated",
        className,
      )}
    >
      <ThemeIcon theme={mounted ? theme : "system"} />
      {compact ? (
        <span className="sr-only">{mounted ? label : THEME_LABELS.system}</span>
      ) : (
        <span className="hidden sm:inline">
          {mounted ? label : THEME_LABELS.system}
        </span>
      )}
    </button>
  );
}
