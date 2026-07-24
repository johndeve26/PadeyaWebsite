import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

export type SectionHeaderProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  align?: "left" | "center";
  tone?: "light" | "dark";
  /**
   * Marketing / homepage sections — stronger eyebrow accent + title depth.
   * Default stays quiet for dashboards and admin.
   */
  variant?: "default" | "display";
  className?: string;
};

export function SectionHeader({
  eyebrow,
  title,
  description,
  action,
  align = "left",
  tone = "light",
  variant = "default",
  className = "",
}: SectionHeaderProps) {
  const dark = tone === "dark";
  const display = variant === "display";

  return (
    <div
      className={cn(
        "flex flex-col gap-2.5",
        align === "center" ? "items-center text-center" : "items-start",
        action ? "sm:flex-row sm:items-end sm:justify-between sm:gap-6" : "",
        className,
      )}
    >
      <div className="max-w-2xl space-y-1.5">
        {eyebrow ? (
          <p
            className={cn(
              "font-bold uppercase",
              display
                ? cn(
                    "inline-flex items-center gap-2.5 text-xs tracking-[0.2em]",
                    align === "center" && "justify-center",
                    // Lime primary fails contrast on light surfaces — keep brand on the bar only.
                    dark ? "text-primary" : "text-heading",
                  )
                : cn(
                    "text-[11px] tracking-[0.18em]",
                    dark ? "text-primary" : "text-muted-foreground",
                  ),
            )}
          >
            {display ? (
              <span
                aria-hidden
                className={cn(
                  "inline-block h-[3px] w-7 shrink-0 rounded-[1px] bg-primary",
                  dark &&
                    "shadow-[0_2px_10px_color-mix(in_srgb,var(--primary)_55%,transparent)]",
                )}
              />
            ) : null}
            <span
              className={cn(
                display &&
                  dark &&
                  "[text-shadow:0_1px_12px_color-mix(in_srgb,var(--primary)_35%,transparent)]",
              )}
            >
              {eyebrow}
            </span>
          </p>
        ) : null}
        <h2
          className={cn(
            "text-balance text-2xl font-extrabold tracking-tight sm:text-3xl md:text-[2.5rem] md:leading-[1.12]",
            dark ? "text-paper" : "text-heading",
            display && "sm:text-[2rem] md:text-[2.65rem]",
            display &&
              dark &&
              "[text-shadow:0_2px_28px_rgb(0_0_0_/0.55)]",
          )}
        >
          {title}
        </h2>
        {description ? (
          <p
            className={cn(
              "max-w-xl text-base leading-relaxed sm:text-[1.05rem]",
              dark ? "text-paper/80" : "text-foreground/75",
            )}
          >
            {description}
          </p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
