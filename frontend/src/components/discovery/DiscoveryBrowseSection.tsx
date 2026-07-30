"use client";

import { useState } from "react";

import { TaxonomyBrowseCard } from "@/components/discovery/TaxonomyBrowseCard";
import type { CategoryNavItem } from "@/components/taxonomy/CategoryNav";
import type { CityNavItem } from "@/components/taxonomy/CityNav";
import { Button, Container } from "@/components/ui";
import {
  categoryBrowseImage,
  cityBrowseImage,
} from "@/lib/discovery/browse-images";
import { cn } from "@/lib/cn";

const DEFAULT_VISIBLE = 8;

export function DiscoveryBrowseSection({
  title,
  description,
  items,
  mode,
  className = "",
  maxVisible = DEFAULT_VISIBLE,
  viewAllLabel,
}: {
  title: string;
  description?: string;
  items: CategoryNavItem[] | CityNavItem[];
  mode: "category" | "city";
  className?: string;
  /** Cap visible shortcuts; remaining unlock via “View all”. */
  maxVisible?: number;
  viewAllLabel?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  if (!items.length) return null;

  const capped =
    !expanded && maxVisible > 0 && items.length > maxVisible
      ? items.slice(0, maxVisible)
      : items;
  const canExpand = maxVisible > 0 && items.length > maxVisible;
  const expandLabel =
    viewAllLabel ||
    (mode === "category" ? "View all categories" : "View all places");

  return (
    <section
      id="browse"
      aria-label={title}
      className={cn(
        "scroll-mt-24 border-b border-border bg-card py-10 sm:py-12",
        className,
      )}
    >
      <Container className="space-y-6">
        <div className="max-w-2xl space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
            Explore
          </p>
          <h2 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
            {title}
          </h2>
          {description ? (
            <p className="max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
              {description}
            </p>
          ) : null}
        </div>
        <ul className="grid auto-rows-fr gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 xl:grid-cols-4">
          {capped.map((item) => {
            const meta =
              typeof item.count === "number"
                ? `${item.count} ${item.count === 1 ? "event" : "events"}`
                : item.hint ||
                  (mode === "category" ? "Browse interest" : "Open city hub");
            const imageUrl =
              "imageUrl" in item ? item.imageUrl : undefined;
            const imageAlt =
              "imageAlt" in item ? item.imageAlt : undefined;
            const focalX = "focalX" in item ? item.focalX : undefined;
            const focalY = "focalY" in item ? item.focalY : undefined;
            return (
              <li key={item.slug} className="h-full">
                <TaxonomyBrowseCard
                  href={item.href}
                  title={item.name}
                  meta={meta}
                  eyebrow={mode === "category" ? "Category" : "City"}
                  image={
                    mode === "category"
                      ? categoryBrowseImage(item.slug, imageUrl)
                      : cityBrowseImage(item.slug, imageUrl)
                  }
                  imageAlt={imageAlt || item.name}
                  focalX={focalX ?? 0.5}
                  focalY={focalY ?? 0.5}
                  className="h-full"
                />
              </li>
            );
          })}
        </ul>
        {canExpand ? (
          <div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setExpanded((v) => !v)}
            >
              {expanded ? "Show fewer" : expandLabel}
            </Button>
          </div>
        ) : null}
      </Container>
    </section>
  );
}
