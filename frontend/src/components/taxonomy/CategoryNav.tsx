import { TaxonomyBrowseCard } from "@/components/discovery/TaxonomyBrowseCard";
import { categoryBrowseImage } from "@/lib/discovery/browse-images";
import { cn } from "@/lib/cn";

export type CategoryNavItem = {
  name: string;
  slug: string;
  href: string;
  hint?: string;
  description?: string;
  count?: number;
  selected?: boolean;
  imageUrl?: string | null;
  imageAlt?: string | null;
  focalX?: number | null;
  focalY?: number | null;
};

export function CategoryNav({
  items,
  className = "",
  compact = false,
}: {
  items: CategoryNavItem[];
  className?: string;
  /** Kept for callers; image cards use a consistent density. */
  compact?: boolean;
}) {
  void compact;
  if (!items.length) return null;

  return (
    <nav aria-label="Categories" className={cn(className)}>
      <ul className="grid auto-rows-fr gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 xl:grid-cols-4">
        {items.map((item) => {
          const meta =
            typeof item.count === "number"
              ? `${item.count} ${item.count === 1 ? "event" : "events"}`
              : item.hint || item.description || "Browse experiences";
          return (
            <li key={item.slug} className="h-full">
              <TaxonomyBrowseCard
                href={item.href}
                title={item.name}
                meta={meta}
                eyebrow="Category"
                image={categoryBrowseImage(item.slug, item.imageUrl)}
                imageAlt={item.imageAlt || item.name}
                focalX={item.focalX ?? 0.5}
                focalY={item.focalY ?? 0.5}
                className={cn(
                  "h-full",
                  item.selected && "ring-2 ring-ink ring-offset-2 ring-offset-background",
                )}
              />
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
