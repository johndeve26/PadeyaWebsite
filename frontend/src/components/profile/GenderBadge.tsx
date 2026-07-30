import { cn } from "@/lib/cn";
import {
  resolveGenderBadge,
  type GenderDisplay,
} from "@/lib/gender";

export type GenderBadgeProps = {
  /** Already-authorized display payload, or a compact male/female value. */
  value?: GenderDisplay | "male" | "female" | null;
  className?: string;
  size?: "sm" | "md";
  /**
   * `default` — brand ink + primary letter (readable on light cards).
   * `onDark` — primary fill + ink letter (readable on ink heroes / passport covers).
   */
  surface?: "default" | "onDark";
};

const surfaceClasses = {
  // Black chip + brand green letter — unique and high-contrast on light UI.
  default: "bg-ink text-primary ring-1 ring-inset ring-primary/45",
  // Lime chip + ink letter — pops on dark passport/hero bands.
  onDark: "bg-primary text-ink ring-1 ring-inset ring-ink/15",
} as const;

const sizeClasses = {
  sm: "min-w-[1.35rem] px-1.5 py-0.5 text-[11px]",
  md: "min-w-[1.5rem] px-2 py-1 text-xs",
} as const;

/**
 * Compact M/F badge. Never pink/blue. Hide when null, prefer_not_to_say, or not visible.
 * Callers must pass backend-filtered data — do not hide a raw private value client-side.
 *
 * Own styles (not Badge tones) so light/dark surfaces stay readable without class fights.
 */
export function GenderBadge({
  value,
  className = "",
  size = "sm",
  surface = "default",
}: GenderBadgeProps) {
  const resolved = resolveGenderBadge(value);
  if (!resolved) return null;

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full font-bold tracking-normal",
        sizeClasses[size],
        surfaceClasses[surface],
        className,
      )}
      title={resolved.label}
    >
      <span aria-hidden>{resolved.short}</span>
      <span className="sr-only">{resolved.label}</span>
    </span>
  );
}
