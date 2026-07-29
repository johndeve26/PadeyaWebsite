import Link from "next/link";

import { MarketingFeatureGrid } from "@/components/marketing/MarketingFeatureGrid";
import { MarketingSection } from "@/components/marketing/MarketingSection";
import { Button, Media } from "@/components/ui";

import { forFansDiscovery } from "./content";

const SCENE_TILES = [
  {
    src: "/demo/events/afrobeats-night-live.svg",
    label: "Music",
    href: "/events/c/music",
  },
  {
    src: "/demo/events/detty-friday-live.svg",
    label: "Nightlife",
    href: "/events/c/nightlife",
  },
  {
    src: "/demo/events/lagos-comedy-jam.svg",
    label: "Comedy",
    href: "/events/c/comedy",
  },
  {
    src: "/brand/browse/city-lagos.svg",
    label: "Lagos",
    href: "/events/city/lagos",
  },
] as const;

export function FansDiscoverySection() {
  return (
    <MarketingSection
      eyebrow="Discovery"
      title="What's happening around you"
      description="Near you, categories, followed hosts, Pàdéyá Picks, and city pages, built for browsing the night, not doom-scrolling a feed."
      headerAction={
        <Link href="/events" className="hidden sm:inline-flex">
          <Button variant="primary" size="lg">
            View all events
          </Button>
        </Link>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {SCENE_TILES.map((tile) => (
          <Link
            key={tile.label}
            href={tile.href}
            className="group relative aspect-[4/3] overflow-hidden rounded-[var(--radius-lg)] border border-border bg-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
          >
            <Media
              src={tile.src}
              alt=""
              className="absolute inset-0 h-full w-full object-cover opacity-90 transition duration-500 group-hover:scale-[1.04]"
            />
            <div
              aria-hidden
              className="absolute inset-0 bg-gradient-to-t from-ink/85 via-ink/20 to-transparent"
            />
            <span className="absolute bottom-3 left-3 text-sm font-extrabold tracking-tight text-paper sm:text-base">
              {tile.label}
            </span>
          </Link>
        ))}
      </div>
      <MarketingFeatureGrid
        items={forFansDiscovery}
        columns={3}
        density="pillars"
      />
      <div className="sm:hidden">
        <Link href="/events" className="block w-full">
          <Button variant="primary" size="lg" className="w-full">
            View all events
          </Button>
        </Link>
      </div>
    </MarketingSection>
  );
}
