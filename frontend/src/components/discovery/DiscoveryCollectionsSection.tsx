import { TaxonomyBrowseCard } from "@/components/discovery/TaxonomyBrowseCard";
import { Container } from "@/components/ui";
import { collectionBrowseImage } from "@/lib/discovery/browse-images";
import { cn } from "@/lib/cn";

export type DiscoveryCollection = {
  label: string;
  href: string;
  hint: string;
  cta?: string;
  count?: number;
  curator?: string;
  coverTone?: "dark" | "light" | "accent";
};

const DEFAULT_COLLECTIONS: DiscoveryCollection[] = [
  {
    label: "This weekend",
    href: "/events/this-weekend",
    hint: "Friday through Sunday. Nights already on the calendar.",
    cta: "View collection",
    curator: "Pàdéyá",
  },
  {
    label: "Free",
    href: "/events/free",
    hint: "Zero-ticket and free RSVP experiences worth showing up for.",
    cta: "View collection",
    curator: "Pàdéyá",
  },
  {
    label: "VIP",
    href: "/events/vip",
    hint: "VIP and VVIP tiers for rooms that go deeper than general entry.",
    cta: "View collection",
    curator: "Pàdéyá",
  },
  {
    label: "Near me",
    href: "/events/near-me",
    hint: "Start with city hubs while precise geo discovery rolls out.",
    cta: "View collection",
    curator: "Pàdéyá",
  },
];

export function DiscoveryCollectionsSection({
  collections = DEFAULT_COLLECTIONS,
  title = "Start with intent",
  description = "Skip the scroll. Jump straight into a useful discovery path.",
  className = "",
}: {
  collections?: DiscoveryCollection[];
  title?: string;
  description?: string;
  className?: string;
}) {
  if (!collections.length) return null;

  return (
    <section
      aria-label={title}
      className={cn(
        "border-b border-border bg-card py-10 sm:py-12",
        className,
      )}
    >
      <Container className="space-y-5">
        <div className="max-w-2xl space-y-1.5">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
            Browse by scene
          </p>
          <h2 className="text-xl font-extrabold tracking-tight text-foreground sm:text-2xl">
            {title}
          </h2>
          {description ? (
            <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
              {description}
            </p>
          ) : null}
        </div>
        <ul className="grid auto-rows-fr gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-4">
          {collections.map((item) => (
            <li key={item.href} className="h-full">
              <TaxonomyBrowseCard
                href={item.href}
                title={item.label}
                meta={
                  typeof item.count === "number"
                    ? `${item.count} upcoming`
                    : item.hint
                }
                image={collectionBrowseImage(item.href)}
                className="h-full"
              />
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
