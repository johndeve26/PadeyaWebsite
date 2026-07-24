"use client";

import Link from "next/link";

import { TaxonomyBrowseCard } from "@/components/discovery/TaxonomyBrowseCard";
import {
  trackHostProfileClick,
  trackLegacyClick,
  trackVaultClick,
} from "@/lib/analytics";
import { cn } from "@/lib/cn";
import {
  browseImageForHref,
  cityBrowseImage,
} from "@/lib/discovery/browse-images";
import { citySlugFromName } from "@/lib/discovery/slugify";
import type { EventItem } from "@/lib/types/events";

type DestinationTone = "host" | "vault" | "memories" | "city" | "category" | "hosts";

const toneClass: Record<DestinationTone, string> = {
  host: "border-ink bg-ink text-paper",
  vault: "border-border bg-muted text-foreground",
  memories: "border-border bg-card text-foreground shadow-[var(--shadow-soft)]",
  city: "border-accent/50 bg-accent/15 text-foreground",
  category: "border-border bg-card text-foreground shadow-[var(--shadow-soft)]",
  hosts: "border-border bg-card text-foreground shadow-[var(--shadow-soft)]",
};

export function RelatedDestinationCard({
  tone,
  eyebrow,
  title,
  description,
  href,
  cta,
  onClick,
  className,
}: {
  tone: DestinationTone;
  eyebrow: string;
  title: string;
  description: string;
  href: string;
  cta: string;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn(
        "group flex min-h-[168px] flex-col justify-between rounded-[var(--radius-xl)] border p-5 transition-transform duration-300 hover:-translate-y-0.5",
        toneClass[tone],
        className,
      )}
    >
      <div className="space-y-2">
        <p
          className={cn(
            "text-[10px] font-extrabold uppercase tracking-[0.14em]",
            tone === "host" ? "text-accent" : "text-muted-foreground",
          )}
        >
          {eyebrow}
        </p>
        <h3 className="text-lg font-extrabold leading-snug tracking-tight">{title}</h3>
        <p
          className={cn(
            "text-sm leading-relaxed",
            tone === "host" ? "text-subtle-foreground" : "text-muted-foreground",
          )}
        >
          {description}
        </p>
      </div>
      <span
        className={cn(
          "mt-5 text-xs font-extrabold uppercase tracking-wide",
          tone === "host"
            ? "text-accent"
            : "text-foreground underline decoration-accent underline-offset-4",
        )}
      >
        {cta}
      </span>
    </Link>
  );
}

export function RelatedHostCard({
  sourceEvent,
  hostName,
  href,
}: {
  sourceEvent: EventItem;
  hostName: string;
  href: string;
}) {
  return (
    <RelatedDestinationCard
      tone="host"
      eyebrow="Explore the host"
      title={`${hostName} Legacy`}
      description="Verified reviews, past events, and upcoming nights from this host."
      href={href}
      cta="Open Legacy Page"
      onClick={() => {
        trackLegacyClick({
          targetEventId: sourceEvent.id,
          hostId: sourceEvent.host_id,
        });
        trackHostProfileClick({
          targetEventId: sourceEvent.id,
          hostId: sourceEvent.host_id,
        });
      }}
    />
  );
}

export function RelatedVaultCard({
  sourceEvent,
  hostName,
  href,
}: {
  sourceEvent: EventItem;
  hostName: string;
  href: string;
}) {
  return (
    <RelatedDestinationCard
      tone="vault"
      eyebrow="Exclusive"
      title="Open the Vault"
      description={`Exclusive content from ${hostName} — unlock by follow, ticket, attendance, VIP, or purchase.`}
      href={href}
      cta="Browse Vault"
      onClick={() => {
        trackVaultClick({
          targetEventId: sourceEvent.id,
          hostId: sourceEvent.host_id,
        });
      }}
    />
  );
}

export function RelatedMemoriesCard({
  sourceEvent,
  hostName,
  href,
}: {
  sourceEvent: EventItem;
  hostName: string;
  href: string;
}) {
  return (
    <RelatedDestinationCard
      tone="memories"
      eyebrow="Memories"
      title={`${hostName} Memories`}
      description="Past nights, recaps, and moments from this host’s Pàdéyá story."
      href={href}
      cta="See Memories"
      onClick={() => {
        trackLegacyClick({
          targetEventId: sourceEvent.id,
          hostId: sourceEvent.host_id,
        });
      }}
    />
  );
}

export function RelatedCityCard({
  city,
  href,
}: {
  city: string;
  href: string;
}) {
  return (
    <TaxonomyBrowseCard
      href={href}
      eyebrow="City hub"
      title={`Explore ${city}`}
      meta={`Browse verified events, hosts, and trending categories in ${city}.`}
      image={cityBrowseImage(citySlugFromName(city))}
      className="h-full min-h-[168px]"
    />
  );
}

export function RelatedCategoryCard({
  categoryName,
  city,
  href,
}: {
  categoryName: string;
  city?: string | null;
  href: string;
}) {
  const title = city
    ? `${categoryName} in ${city}`
    : `More ${categoryName.toLowerCase()} events`;
  const description = city
    ? `Find similar ${categoryName.toLowerCase()} nights and live experiences in ${city}.`
    : `Find similar nights, live shows, and experiences in ${categoryName.toLowerCase()}.`;

  return (
    <TaxonomyBrowseCard
      href={href}
      eyebrow="Category hub"
      title={title}
      meta={description}
      image={browseImageForHref(href)}
      className="h-full min-h-[168px]"
    />
  );
}

export function RelatedHostsHubCard({
  city,
  href,
}: {
  city?: string | null;
  href: string;
}) {
  return (
    <TaxonomyBrowseCard
      href={href}
      eyebrow="Hosts"
      title={city ? `Verified hosts in ${city}` : "Verified hosts on Pàdéyá"}
      meta={
        city
          ? `Discover trusted organizers throwing nights in ${city}.`
          : "Discover trusted organizers across the marketplace."
      }
      image={browseImageForHref(href)}
      className="h-full min-h-[168px]"
    />
  );
}
