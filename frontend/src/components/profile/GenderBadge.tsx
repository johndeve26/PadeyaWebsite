import { Badge } from "@/components/ui";
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
};

/**
 * Neutral M/F badge. Never pink/blue. Hide when null, prefer_not_to_say, or not visible.
 * Callers must pass backend-filtered data — do not hide a raw private value client-side.
 */
export function GenderBadge({
  value,
  className = "",
  size = "sm",
}: GenderBadgeProps) {
  const resolved = resolveGenderBadge(value);
  if (!resolved) return null;

  return (
    <Badge
      tone="neutral"
      size={size}
      className={cn("normal-case tracking-normal", className)}
      title={resolved.label}
    >
      <span aria-hidden>{resolved.short}</span>
      <span className="sr-only">{resolved.label}</span>
    </Badge>
  );
}
