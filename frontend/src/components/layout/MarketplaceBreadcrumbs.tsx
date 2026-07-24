"use client";

import { Container } from "@/components/ui";
import { Breadcrumb, type BreadcrumbItem } from "@/components/ui/Breadcrumb";
import { cn } from "@/lib/cn";

export function MarketplaceBreadcrumbs({
  items,
  className = "",
}: {
  items: BreadcrumbItem[];
  className?: string;
}) {
  if (items.length === 0) return null;

  return (
    <div
      className={cn(
        "border-b border-border/90 bg-[linear-gradient(180deg,color-mix(in_srgb,var(--primary)_6%,var(--card))_0%,var(--card)_100%)]",
        className,
      )}
    >
      <Container className="flex min-w-0 items-center gap-3 py-2.5">
        <span
          aria-hidden
          className="hidden h-4 w-1 shrink-0 rounded-full bg-accent sm:block"
        />
        <Breadcrumb items={items} className="min-w-0 flex-1" />
      </Container>
    </div>
  );
}
