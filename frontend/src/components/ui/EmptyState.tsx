import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Card } from "./Card";

export function EmptyState({
  title,
  description,
  action,
  icon,
  className = "",
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <Card
      variant="muted"
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-6 py-12 text-center sm:py-14",
        className,
      )}
    >
      {icon ? (
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-ink text-primary">
          {icon}
        </div>
      ) : (
        <div className="h-1.5 w-12 rounded-full bg-primary" aria-hidden />
      )}
      <h3 className="text-lg font-extrabold tracking-tight text-heading sm:text-xl">
        {title}
      </h3>
      {description ? (
        <p className="max-w-md text-sm leading-relaxed text-muted-foreground sm:text-base">
          {description}
        </p>
      ) : null}
      {action ? <div className="pt-1">{action}</div> : null}
    </Card>
  );
}
