import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

type Tone = "info" | "success" | "warning" | "danger";

const toneClasses: Record<Tone, string> = {
  info: "border-info/40 bg-info-surface text-info-foreground",
  success: "border-success/40 bg-success-surface text-success-foreground",
  warning: "border-warning/45 bg-warning-surface text-warning-foreground",
  danger: "border-danger/45 bg-danger-surface text-danger-foreground",
};

export function Alert({
  tone = "info",
  title,
  children,
  action,
  className = "",
}: {
  tone?: Tone;
  title?: string;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      role="status"
      className={cn(
        "flex flex-col gap-2 rounded-[var(--radius-md)] border px-4 py-3 sm:flex-row sm:items-start sm:justify-between",
        toneClasses[tone],
        className,
      )}
    >
      <div className="min-w-0 space-y-1">
        {title ? (
          <p className="text-sm font-bold tracking-tight text-current">{title}</p>
        ) : null}
        {children ? (
          <div className="text-sm leading-relaxed text-current">{children}</div>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
