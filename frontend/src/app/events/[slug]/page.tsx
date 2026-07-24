import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { EventDetailClient } from "./EventDetailClient";
import { formatPublicPlaceLabel } from "@/lib/event-privacy";
import {
  buildEventMetadata,
  eventJsonLd,
  isEventSeoIndexable,
} from "@/lib/seo/event-metadata";
import { JsonLdScript, breadcrumbJsonLd } from "@/lib/seo/jsonld";
import { fetchPublicJson } from "@/lib/seo/public-fetch";
import { NOINDEX_ROBOTS } from "@/lib/seo/noindex";
import { siteOrigin } from "@/lib/seo/site";
import type { EventItem } from "@/lib/types/events";

export const revalidate = 120;

async function loadEvent(slug: string): Promise<EventItem | null> {
  const { data, status } = await fetchPublicJson<EventItem>(
    `/events/${encodeURIComponent(slug)}`,
    { revalidate: 120 },
  );
  if (status === 404 || !data) return null;
  return data;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const event = await loadEvent(slug);
  if (!event) {
    return { title: "Event", robots: NOINDEX_ROBOTS };
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
  if (!event) notFound();

  const crumbs: { label: string; href?: string }[] = [
    { label: "Home", href: "/" },
    { label: "Events", href: "/events" },
  ];
  const placeLabel = formatPublicPlaceLabel(event);
  const cityForCrumb =
    event.location_address_revealed === true ||
    event.location_visibility === "area_only" ||
    event.location_visibility === "full_public"
      ? event.city
      : null;
  if (cityForCrumb) {
    const citySlug = cityForCrumb.trim().toLowerCase().replace(/\s+/g, "-");
    crumbs.push({ label: cityForCrumb, href: `/events/city/${citySlug}` });
  } else if (
    placeLabel &&
    event.location_visibility !== "online_only" &&
    placeLabel !== "Online Event"
  ) {
    crumbs.push({ label: placeLabel });
  }
  if (event.category?.name && event.category.slug) {
    crumbs.push({
      label: event.category.name,
      href: `/events/c/${event.category.slug}`,
    });
  }
  crumbs.push({ label: event.title || "Event" });

  const schema = eventJsonLd(event);
  const showBreadcrumbLd = isEventSeoIndexable(event);

  return (
    <>
      {schema ? <JsonLdScript data={schema} /> : null}
      {showBreadcrumbLd ? (
        <JsonLdScript data={breadcrumbJsonLd(crumbs, siteOrigin())} />
      ) : null}
      <Suspense fallback={null}>
        <EventDetailClient initialEvent={event} />
      </Suspense>
    </>
  );
}
