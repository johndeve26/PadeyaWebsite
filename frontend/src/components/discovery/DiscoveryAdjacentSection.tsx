import Link from "next/link";

import { TaxonomyBrowseCard } from "@/components/discovery/TaxonomyBrowseCard";
import { Button, Container } from "@/components/ui";
import { browseImageForHref } from "@/lib/discovery/browse-images";
import { cn } from "@/lib/cn";
import { SPONSORSHIP_HOSTS_PATH } from "@/lib/sponsor-marketplace-paths";

export type AdjacentLink = {
  label: string;
  href: string;
  hint?: string;
  eyebrow?: string;
  count?: number;
  /** Optional explicit art; otherwise resolved from href. */
  image?: string;
  /** @deprecated Glyphs replaced by browse images. */
  iconSlug?: string;
};

export function DiscoveryAdjacentSection({
  links,
  className = "",
  title = "Keep exploring",
  description = "More ways into cities, categories, and hosts on Pàdéyá.",
}: {
  links: AdjacentLink[];
  className?: string;
  title?: string;
  description?: string;
}) {
  if (!links.length) return null;

  return (
    <section
      aria-label={title}
      className={cn(
        "border-t border-border bg-muted py-10 sm:py-12",
        className,
      )}
    >
      <Container className="flex flex-col gap-6">
        <div className="max-w-2xl space-y-1.5">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
            Explore more on Pàdéyá
          </p>
          <h2 className="text-xl font-extrabold tracking-tight text-foreground sm:text-2xl">
            {title}
          </h2>
          <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
            {description}
          </p>
        </div>
        <ul className="grid auto-rows-fr gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3">
          {links.map((link) => {
            const meta =
              typeof link.count === "number"
                ? link.hint
                  ? `${link.hint} · ${link.count} upcoming`
                  : `${link.count} upcoming`
                : link.hint || "Browse on Pàdéyá";
            return (
              <li key={link.href} className="h-full">
                <TaxonomyBrowseCard
                  href={link.href}
                  title={link.label}
                  meta={meta}
                  eyebrow={link.eyebrow}
                  image={link.image || browseImageForHref(link.href)}
                  className="h-full"
                />
              </li>
            );
          })}
        </ul>
        <div className="flex flex-wrap gap-3">
          <Link href="/hosts">
            <Button variant="secondary" size="md" className="padeya-btn-micro">
              Browse hosts
            </Button>
          </Link>
          <Link href={SPONSORSHIP_HOSTS_PATH}>
            <Button variant="primary" size="md" className="padeya-btn-ripple">
              Sponsor-ready hosts
            </Button>
          </Link>
        </div>
      </Container>
    </section>
  );
}
