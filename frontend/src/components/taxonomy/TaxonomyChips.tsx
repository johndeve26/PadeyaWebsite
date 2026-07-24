import Link from "next/link";

import { cn } from "@/lib/cn";

export type TaxonomyChip = {
  label: string;
  href?: string;
};

export function TaxonomyChips({
  chips,
  className = "",
}: {
  chips: TaxonomyChip[];
  className?: string;
}) {
  if (!chips.length) return null;

  return (
    <ul className={cn("flex flex-wrap gap-2", className)}>
      {chips.map((chip) => {
        const classNameChip = cn(
          "inline-flex items-center rounded-full border border-border bg-surface-muted px-3 py-1.5",
          "text-xs font-semibold text-foreground transition-colors",
          "dark:bg-surface-elevated",
          chip.href
            ? "hover:border-border-strong/40 hover:bg-muted"
            : "",
        );

        return (
          <li key={`${chip.label}-${chip.href ?? "plain"}`}>
            {chip.href ? (
              <Link href={chip.href} className={classNameChip}>
                {chip.label}
              </Link>
            ) : (
              <span className={classNameChip}>{chip.label}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
