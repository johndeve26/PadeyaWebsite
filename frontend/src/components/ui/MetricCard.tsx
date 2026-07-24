import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Card } from "./Card";

export function MetricCard({
  label,
  value,
  description,
  action,
  className = "",
}: {
  label: string;
  value: ReactNode;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("flex h-full flex-col gap-3", className)}>
      <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
        {label}
      </p>
      <div className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
        {value}
      </div>
      {description ? (
        <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
      ) : null}
      {action ? <div className="mt-auto pt-1">{action}</div> : null}
    </Card>
  );
}
