import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** Shared surface for Studio item rows (agenda, people, tickets, questions). */
export function StudioItemCard({
  title,
  subtitle,
  actions,
  children,
  className,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "space-y-4 rounded-[var(--radius-lg)] border border-border bg-card p-4 shadow-[var(--shadow-soft)] sm:p-5 dark:bg-surface-elevated",
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-border/80 pb-3">
        <div className="min-w-0">
          <p className="text-sm font-extrabold tracking-tight text-foreground">
            {title}
          </p>
          {subtitle ? (
            <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
              {subtitle}
            </p>
          ) : null}
        </div>
        {actions ? (
          <div className="flex flex-wrap items-center gap-1">{actions}</div>
        ) : null}
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

export function StudioFieldGroup({
  title,
  description,
  children,
  className,
}: {
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "space-y-3 rounded-[var(--radius-md)] border border-border/80 bg-muted/40 p-4",
        className,
      )}
    >
      {title || description ? (
        <div>
          {title ? (
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
              {title}
            </p>
          ) : null}
          {description ? (
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              {description}
            </p>
          ) : null}
        </div>
      ) : null}
      {children}
    </div>
  );
}

export function StudioMicrocopy({ children }: { children: ReactNode }) {
  return (
    <p className="text-sm leading-relaxed text-muted-foreground">{children}</p>
  );
}
