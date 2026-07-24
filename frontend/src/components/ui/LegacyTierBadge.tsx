import { cn } from "@/lib/cn";

import { Badge } from "./Badge";

const TIER_STYLES: Record<
  string,
  { label: string; className: string }
> = {
  new_host: {
    label: "New Host",
    className: "bg-muted text-muted-foreground ring-border",
  },
  "new host": {
    label: "New Host",
    className: "bg-muted text-muted-foreground ring-border",
  },
  rising: {
    label: "Rising",
    className: "bg-success-surface text-success-foreground ring-primary/40",
  },
  established: {
    label: "Established",
    className:
      "bg-ink text-paper ring-ink shadow-[0_0_0_1px_color-mix(in_srgb,var(--primary)_35%,transparent)]",
  },
  certified: {
    label: "Certified",
    className:
      "bg-[linear-gradient(135deg,var(--surface-dark),var(--dark-gray))] text-primary ring-primary/50 shadow-[var(--shadow-glow)]",
  },
  icon: {
    label: "Icon",
    className:
      "bg-[linear-gradient(135deg,var(--ink),var(--dark-gray)_60%,color-mix(in_srgb,var(--primary)_35%,transparent))] text-paper ring-primary shadow-[var(--shadow-glow)]",
  },
  legend: {
    label: "Legend",
    className:
      "bg-[linear-gradient(120deg,var(--surface-dark)_0%,var(--ink)_55%,color-mix(in_srgb,var(--primary)_55%,transparent)_140%)] text-paper ring-primary shadow-[var(--shadow-glow)]",
  },
};

export function LegacyTierBadge({
  tier,
  className = "",
}: {
  tier: string;
  className?: string;
}) {
  const key = tier.toLowerCase().replace(/\s+/g, " ").trim();
  const style = TIER_STYLES[key] ?? TIER_STYLES[key.replace(/ /g, "_")];

  if (!style) {
    return (
      <Badge tone="accent" className={className}>
        {tier}
      </Badge>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-[0.1em] ring-1 ring-inset",
        style.className,
        className,
      )}
    >
      <span
        aria-hidden
        className="h-1.5 w-1.5 rounded-full bg-primary ring-1 ring-paper/30"
      />
      {style.label}
    </span>
  );
}
