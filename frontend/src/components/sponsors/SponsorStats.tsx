import { cn } from "@/lib/cn";
import { formatCompactNumber } from "@/lib/sponsor-host-presentation";

export type SponsorStatItem = {
  label: string;
  value: string | number;
  hint?: string;
};

export function SponsorStats({
  items,
  tone = "dark",
  className = "",
}: {
  items: SponsorStatItem[];
  tone?: "dark" | "light";
  className?: string;
}) {
  const dark = tone === "dark";

  return (
    <div
      className={cn(
        "grid grid-cols-2 gap-2 sm:gap-3 lg:grid-cols-4",
        className,
      )}
    >
      {items.map((item) => (
        <div
          key={item.label}
          className={cn(
            "rounded-[var(--radius-md)] border px-3 py-2.5 sm:px-3.5 sm:py-3",
            dark
              ? "border-paper/10 bg-paper/[0.04] backdrop-blur-sm"
              : "border-border bg-card shadow-[var(--shadow-soft)] dark:bg-surface-elevated",
          )}
        >
          <p
            className={cn(
              "text-lg font-extrabold tracking-tight sm:text-xl",
              dark ? "text-paper" : "text-foreground",
            )}
          >
            {typeof item.value === "number"
              ? formatCompactNumber(item.value)
              : item.value}
          </p>
          <p
            className={cn(
              "mt-0.5 text-[10px] font-bold uppercase tracking-[0.12em]",
              dark ? "text-subtle-foreground" : "text-muted-foreground",
            )}
          >
            {item.label}
          </p>
          {item.hint ? (
            <p
              className={cn(
                "mt-0.5 text-xs",
                dark ? "text-subtle-foreground/80" : "text-muted-foreground",
              )}
            >
              {item.hint}
            </p>
          ) : null}
        </div>
      ))}
    </div>
  );
}
