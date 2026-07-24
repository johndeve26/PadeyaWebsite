import type { ReactNode } from "react";

import { Card } from "@/components/ui";
import { cn } from "@/lib/cn";

export function EventStudioSection({
  title,
  description,
  children,
  action,
  eyebrow,
  className,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  action?: ReactNode;
  eyebrow?: string;
  className?: string;
}) {
  return (
    <Card
      className={cn(
        "space-y-6 border-border shadow-[var(--shadow-soft)]",
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border pb-5">
        <div className="min-w-0 max-w-2xl">
          {eyebrow ? (
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
              {eyebrow}
            </p>
          ) : null}
          <h3
            className={cn(
              "text-xl font-extrabold tracking-tight text-foreground",
              eyebrow ? "mt-1" : "",
            )}
          >
            {title}
          </h3>
          {description ? (
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              {description}
            </p>
          ) : null}
        </div>
        {action}
      </div>
      <div className="space-y-5">{children}</div>
    </Card>
  );
}
