"use client";

import Link from "next/link";
import { useDeferredValue, useState } from "react";

import { FaqAccordion } from "@/components/faq/FaqAccordion";
import { FaqCategoryNav } from "@/components/faq/FaqCategoryNav";
import { EmptyState, Input } from "@/components/ui";
import {
  filterFaqCategories,
  type FaqCategory,
} from "@/lib/faq/faq-content";

export function FaqExplorer({
  categories,
}: {
  categories: readonly FaqCategory[];
}) {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const filtered = filterFaqCategories(categories, deferredQuery);
  const searching = deferredQuery.trim().length > 0;

  return (
    <div className="space-y-10 sm:space-y-12">
      <div className="mx-auto max-w-2xl">
        <label className="sr-only" htmlFor="faq-search">
          Search questions
        </label>
        <Input
          id="faq-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search questions…"
          autoComplete="off"
          className="h-12 border-border bg-card text-base shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
        />
      </div>

      {!searching ? (
        <FaqCategoryNav categories={categories} />
      ) : null}

      {searching && filtered.length === 0 ? (
        <EmptyState
          title="No answer found. Contact support."
          description="Try another keyword, browse categories, or open Support."
          action={
            <Link href="/support" className="text-sm font-semibold text-primary-text">
              Contact support
            </Link>
          }
        />
      ) : (
        <div className="space-y-12 sm:space-y-14">
          {filtered.map((category) => (
            <section
              key={category.id}
              id={category.id}
              className="scroll-mt-24"
              aria-labelledby={`${category.id}-heading`}
            >
              <h2
                id={`${category.id}-heading`}
                className="font-display text-2xl font-extrabold tracking-tight text-heading sm:text-3xl"
              >
                {category.title}
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {category.items.length}{" "}
                {category.items.length === 1 ? "question" : "questions"}
              </p>
              <div className="mt-6">
                <FaqAccordion items={category.items} />
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
