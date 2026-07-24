"use client";

import { CollectionLandingClient } from "@/components/discovery/CollectionLandingClient";
import type { BreadcrumbItem } from "@/components/ui/Breadcrumb";
import {
  formatHubMeta,
  formatLandingPath,
  type FormatHubKey,
} from "@/lib/discovery/format-landing";

export function FormatLandingClient({
  formatKey,
  crumbs,
}: {
  formatKey: FormatHubKey;
  crumbs: BreadcrumbItem[];
}) {
  const meta = formatHubMeta(formatKey);

  return (
    <CollectionLandingClient
      crumbs={crumbs}
      basePath={formatLandingPath(formatKey)}
      filters={{ event_format: formatKey }}
      copy={{
        eyebrow: meta.eyebrow,
        title: meta.title,
        description: meta.description,
        heroImage: meta.heroImage,
        sectionEyebrow: "Featured",
        sectionTitle: `Nights worth showing up for`,
        sectionTitleWeekend: `This weekend · ${meta.emptyLabel}`,
        sectionDescription: "Verified tickets and privacy-safe location labels.",
        emptyTitle: `No ${meta.emptyLabel} events yet`,
        emptyTitleWeekend: `No weekend ${meta.emptyLabel} events yet`,
        emptyDescription:
          "Check back soon, or browse another format from the home page.",
        citySectionTitle: `${meta.eyebrow} by city`,
        cityCountSuffix: "upcoming",
        jumpInTitle: "Narrow the night",
        jumpInDescription:
          "Weekend only, or jump back to the full marketplace.",
        ctaTitle: "Ready for a different format?",
        ctaDescription:
          "In person, online, and hybrid — pick how you want in.",
        secondaryAction: { href: "/events/this-weekend", label: "This weekend" },
      }}
    />
  );
}
