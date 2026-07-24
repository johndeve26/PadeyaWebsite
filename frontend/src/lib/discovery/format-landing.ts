/** Event format hub keys used in browse tiles and URLs. */
export type FormatHubKey = "public" | "online" | "hybrid";

const FORMAT_HUBS: Record<
  FormatHubKey,
  {
    path: string;
    title: string;
    eyebrow: string;
    description: string;
    emptyLabel: string;
    heroImage: string;
  }
> = {
  public: {
    path: "/events/in-person",
    title: "Show up in the room.",
    eyebrow: "In person",
    description:
      "Stages, venues, and nights you have to be there for — verified tickets, real hosts.",
    emptyLabel: "in-person",
    heroImage: "/brand/browse/when-person.svg",
  },
  online: {
    path: "/events/online",
    title: "Join from anywhere.",
    eyebrow: "Online",
    description:
      "Streams, virtual rooms, and remote-first nights — same Pàdéyá tickets, no commute.",
    emptyLabel: "online",
    heroImage: "/brand/browse/when-online.svg",
  },
  hybrid: {
    path: "/events/hybrid",
    title: "Both ways in.",
    eyebrow: "Hybrid",
    description:
      "Attend in the room or join remotely on the same night — pick the seat that fits.",
    emptyLabel: "hybrid",
    heroImage: "/brand/browse/when-hybrid.svg",
  },
};

export function isFormatHubKey(value: string): value is FormatHubKey {
  return value === "public" || value === "online" || value === "hybrid";
}

export function formatHubMeta(key: FormatHubKey) {
  return FORMAT_HUBS[key];
}

export function formatLandingPath(key: FormatHubKey): string {
  return FORMAT_HUBS[key].path;
}

/** Map a public path slug back to the event_type filter value. */
export function formatKeyFromPathSlug(
  slug: string,
): FormatHubKey | null {
  if (slug === "in-person") return "public";
  if (slug === "online") return "online";
  if (slug === "hybrid") return "hybrid";
  return null;
}
