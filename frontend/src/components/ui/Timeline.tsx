import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

export type TimelineItem = {
  id: string;
  title: string;
  description?: string;
  meta?: ReactNode;
};

export function Timeline({
  items,
  className = "",
}: {
  items: TimelineItem[];
  className?: string;
}) {
  return (
    <ol className={cn("relative space-y-0 border-l border-border pl-6", className)}>
      {items.map((item) => (
        <li key={item.id} className="relative pb-8 last:pb-0">
          <span className="absolute -left-[1.6rem] top-1 flex h-3 w-3 items-center justify-center rounded-full bg-primary ring-4 ring-background" />
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-bold text-foreground">{item.title}</h3>
              {item.meta}
            </div>
            {item.description ? (
              <p className="text-sm leading-relaxed text-muted-foreground">
                {item.description}
              </p>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
