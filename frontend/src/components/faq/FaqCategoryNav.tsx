"use client";

import Link from "next/link";

import { ScrollHintNav } from "@/components/ui/ScrollHintNav";
import type { FaqCategory } from "@/lib/faq/faq-content";
import { cn } from "@/lib/cn";

export function FaqCategoryNav({
  categories,
}: {
  categories: readonly Pick<FaqCategory, "id" | "title">[];
}) {
  return (
    <ScrollHintNav
      aria-label="FAQ categories"
      fadeFrom="var(--background)"
      className="rounded-[var(--radius-xl)] border border-border/80 bg-card/60 p-2 dark:bg-surface-elevated/80"
      scrollClassName="flex gap-2 px-1 py-1"
    >
      {categories.map((category) => (
        <Link
          key={category.id}
          href={`#${category.id}`}
          className={cn(
            "shrink-0 rounded-md border border-transparent px-3 py-2 text-sm font-semibold text-muted-foreground transition",
            "hover:border-primary/30 hover:bg-paper/[0.04] hover:text-heading",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50",
          )}
        >
          {category.title}
        </Link>
      ))}
    </ScrollHintNav>
  );
}
