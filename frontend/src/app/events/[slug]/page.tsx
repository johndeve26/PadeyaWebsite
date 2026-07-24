import type { Metadata } from "next";
import { Suspense } from "react";

import { EventDetailClient } from "./EventDetailClient";
import { formatPublicPlaceLabel } from "@/lib/event-privacy";
import { buildEventMetadata, eventJsonLd } from "@/lib/seo/event-metadata";
import { JsonLdScript, breadcrumbJsonLd } from "@/lib/seo/jsonld";
import { siteOrigin } from "@/lib/seo/site";
import type { EventItem } from "@/lib/types/events";

export const revalidate = 120;

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_PREFIX = process.env.NEXT_PUBLIC_API_PREFIX ?? "/api/v1";

async function loadEvent(slug: string): Promise<EventItem | null> {
  try {
    const res = await fetch(`${API_URL}${API_PREFIX}/events/${slug}`, {
      next: { revalidate: 120 },
    });
    if (!res.ok) return null;
    return (await res.json()) as EventItem;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const event = await loadEvent(slug);
  if (!event) {
    return { title: "Event", robots: { index: false, follow: false } };
  }
  return buildEventMetadata(event);
}

export default async function EventDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const event = await loadEvent(slug);

  const crumbs: { label: string; href?: string }[] = [
    { label: "Home", href: "/" },
    { label: "Events", href: "/events" },
  ];
  // Prefer privacy-safe place label over raw city when venue is hidden.
  const placeLabel = event ? formatPublicPlaceLabel(event) : null;
  const cityForCrumb =
    event?.location_address_revealed === true ||
    event?.location_visibility === "area_only" ||
    event?.location_visibility === "full_public"
      ? event?.city
      : null;
  if (cityForCrumb) {
    const citySlug = cityForCrumb.trim().toLowerCase().replace(/\s+/g, "-");
    crumbs.push({ label: cityForCrumb, href: `/events/city/${citySlug}` });
  } else if (
    placeLabel &&
    event?.location_visibility !== "online_only" &&
    placeLabel !== "Online Event"
  ) {
    crumbs.push({ label: placeLabel });
  }
  if (event?.category?.name && event.category.slug) {
    crumbs.push({
      label: event.category.name,
      href: `/events/c/${event.category.slug}`,
    });
  }
  crumbs.push({ label: event?.title || "Event" });

  return (
    <>
      {event ? (
        <>
          <JsonLdScript data={eventJsonLd(event)} />
          <JsonLdScript data={breadcrumbJsonLd(crumbs, siteOrigin())} />
        </>
      ) : null}
      <Suspense fallback={null}>
        <EventDetailClient initialEvent={event} />
      </Suspense>
    </>
  );
}
