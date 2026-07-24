import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Badge } from "./Badge";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  size = "default",
  className = "",
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  /** operational = compact private-dashboard titles (host workspace). */
  size?: "default" | "operational";
  className?: string;
}) {
  const operational = size === "operational";

  return (
    <div
      className={cn(
        "flex flex-col gap-4 border-b border-border sm:flex-row sm:items-end sm:justify-between sm:gap-6",
        operational ? "pb-4 sm:pb-5" : "pb-6 sm:pb-8",
        className,
      )}
    >
      <div className="min-w-0 max-w-3xl space-y-2.5">
        {eyebrow ? <Badge tone="accent">{eyebrow}</Badge> : null}
        <h1
          className={cn(
            "text-balance break-words font-bold tracking-tight text-heading",
            operational
              ? "text-xl sm:text-2xl"
              : "text-2xl font-extrabold sm:text-3xl lg:text-4xl",
          )}
        >
          {title}
        </h1>
        {description ? (
          <p
            className={cn(
              "max-w-2xl text-pretty leading-relaxed text-muted-foreground",
              operational ? "text-sm" : "text-base sm:text-lg",
            )}
          >
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex w-full min-w-0 flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
          {actions}
        </div>
      ) : null}
    </div>
  );
}
