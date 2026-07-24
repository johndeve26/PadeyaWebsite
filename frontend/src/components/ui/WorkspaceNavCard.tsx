import Link from "next/link";
import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Card } from "./Card";

export type WorkspaceNavItem = {
  href: string;
  title: string;
  description: string;
  meta?: string;
  icon?: ReactNode;
};

/** Premium navigation card for dashboard hubs — replaces “Open / Manage” scaffold tiles. */
export function WorkspaceNavCard({
  href,
  title,
  description,
  meta,
  icon,
  className = "",
}: WorkspaceNavItem & { className?: string }) {
  return (
    <Link href={href} className={cn("group block h-full", className)}>
      <Card
        hover
        className="flex h-full flex-col gap-3 padeya-stat-surface"
      >
        <div className="flex items-start justify-between gap-3">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            {meta || "Workspace"}
          </p>
          {icon ? (
            <span className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-sm)] bg-ink text-sm font-extrabold text-accent">
              {icon}
            </span>
          ) : (
            <span className="text-lg font-extrabold text-accent transition-transform group-hover:translate-x-0.5">
              →
            </span>
          )}
        </div>
        <h3 className="text-xl font-extrabold tracking-tight text-foreground">
          {title}
        </h3>
        <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
          {description}
        </p>
      </Card>
    </Link>
  );
}

export function WorkspaceNavGrid({
  items,
  className = "",
}: {
  items: WorkspaceNavItem[];
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid gap-4 sm:grid-cols-2 xl:grid-cols-3",
        className,
      )}
    >
      {items.map((item) => (
        <WorkspaceNavCard key={item.href} {...item} />
      ))}
    </div>
  );
}
