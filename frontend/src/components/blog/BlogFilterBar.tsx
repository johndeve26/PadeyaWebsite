"use client";

import Link from "next/link";

import type { BlogCategory } from "@/lib/blog-api";
import { trackBlogFilterUsed } from "@/lib/analytics";

export function BlogFilterBar({
  categories,
  activeSlug,
}: {
  categories: BlogCategory[];
  activeSlug?: string | null;
}) {
  return (
    <div className="sticky top-0 z-20 -mx-4 border-b border-border bg-background/90 px-4 py-3 backdrop-blur-md sm:mx-0 sm:rounded-[var(--radius-md)] sm:border sm:px-3">
      <div className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <Link
          href="/blog"
          onClick={() =>
            trackBlogFilterUsed({ filterType: "category", filterValue: "all" })
          }
          className={
            !activeSlug
              ? "shrink-0 rounded-full bg-primary px-3.5 py-1.5 text-xs font-bold text-primary-foreground"
              : "shrink-0 rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold text-muted-foreground hover:border-primary/40 hover:text-foreground"
          }
        >
          All
        </Link>
        {categories.map((c) => (
          <Link
            key={c.id}
            href={`/blog/category/${c.slug}`}
            onClick={() =>
              trackBlogFilterUsed({
                filterType: "category",
                filterValue: c.slug,
              })
            }
            className={
              activeSlug === c.slug
                ? "shrink-0 rounded-full bg-primary px-3.5 py-1.5 text-xs font-bold text-primary-foreground"
                : "shrink-0 rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold text-muted-foreground hover:border-primary/40 hover:text-foreground"
            }
          >
            {c.name}
          </Link>
        ))}
      </div>
    </div>
  );
}
