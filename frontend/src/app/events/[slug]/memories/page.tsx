import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { EventMemoriesGallery } from "@/components/memories/EventMemoriesGallery";
import { EventMemoriesViewTracker } from "@/components/memories/EventMemoriesViewTracker";
import { ExternalGalleryLink } from "@/components/memories/ExternalGalleryLink";
import { FanMemoryUploadCard } from "@/components/memories/FanMemoryUploadCard";
import { Badge, Button, Container, SectionHeader } from "@/components/ui";
import { fetchMemoryBySlugServer } from "@/lib/memories/public-server";
import { buildPageMetadata, getCanonicalSiteOrigin } from "@/lib/seo/site";

export const revalidate = 120;

type PageProps = {
  params: Promise<{ slug: string }>;
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const memory = await fetchMemoryBySlugServer(slug);
  if (!memory) {
    return { title: "Memories", robots: { index: false, follow: false } };
  }
  const title = `${memory.event_title} Memories – Event Photos`;
  const description = `Relive ${memory.event_title}${
    memory.city ? ` in ${memory.city}` : ""
  } with photos shared by the host and verified attendees.`;
  const indexable = Boolean(memory.seo_indexable);
  return buildPageMetadata({
    title,
    description,
    path: `/events/${memory.event_slug}/memories`,
    noIndex: !indexable,
  });
}

export default async function EventMemoriesPage({ params }: PageProps) {
  const { slug } = await params;
  const memory = await fetchMemoryBySlugServer(slug);
  if (!memory) notFound();

  const hostMedia = memory.host_media?.length
    ? memory.host_media
    : memory.media.filter((m) => (m.uploader_role || "host") === "host");
  const communityMedia = memory.community_media?.length
    ? memory.community_media
    : memory.media.filter((m) => m.uploader_role === "fan");
  const counts = memory.counts ?? {
    memory_count: memory.media.length,
    host_memory_count: hostMedia.length,
    community_memory_count: communityMedia.length,
    contributor_count: 0,
  };

  const origin = getCanonicalSiteOrigin();
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: `${memory.event_title} Memories`,
    description: memory.host_recap_note || undefined,
    url: `${origin}/events/${memory.event_slug}/memories`,
    breadcrumb: {
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Home", item: `${origin}/` },
        {
          "@type": "ListItem",
          position: 2,
          name: "Events",
          item: `${origin}/events`,
        },
        {
          "@type": "ListItem",
          position: 3,
          name: memory.event_title,
          item: `${origin}/events/${memory.event_slug}`,
        },
        {
          "@type": "ListItem",
          position: 4,
          name: "Memories",
          item: `${origin}/events/${memory.event_slug}/memories`,
        },
      ],
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <EventMemoriesViewTracker eventId={memory.event_id} />
      <Container className="py-10 sm:py-14">
        <div className="mx-auto max-w-3xl">
          <div className="mb-6 flex flex-wrap items-center gap-2">
            <Badge tone="info">Past event</Badge>
            <Link
              href={`/events/${memory.event_slug}`}
              className="text-sm font-semibold text-primary-text underline-offset-4 hover:underline"
            >
              Event page
            </Link>
          </div>

          <SectionHeader
            eyebrow="Event Memories"
            title={memory.event_title}
            description={`${formatDate(memory.start_datetime)}${
              memory.city ? ` · ${memory.city}` : ""
            } · Hosted by ${memory.host_display_name}`}
          />

          <p className="mt-4 text-sm text-muted-foreground">
            {counts.memory_count} memories
            {counts.contributor_count
              ? ` · ${counts.contributor_count} verified contributors`
              : ""}
          </p>

          {memory.host_recap_note ? (
            <p className="mt-6 whitespace-pre-wrap text-base leading-relaxed text-body">
              {memory.host_recap_note}
            </p>
          ) : null}

          <div className="mt-8">
            <FanMemoryUploadCard
              eventId={memory.event_id}
              eventSlug={memory.event_slug}
              eventTitle={memory.event_title}
            />
          </div>
        </div>

        <div className="mt-10">
          <EventMemoriesGallery
            eventId={memory.event_id}
            hostDisplayName={memory.host_display_name}
            hostMedia={hostMedia}
            communityMedia={communityMedia}
            hostCount={counts.host_memory_count}
            communityCount={counts.community_memory_count}
          />
        </div>

        {memory.external_gallery_url ? (
          <div className="mt-8">
            <ExternalGalleryLink
              url={memory.external_gallery_url}
              label={memory.external_gallery_label}
              eventId={memory.event_id}
              eventTitle={memory.event_title}
            />
          </div>
        ) : null}

        <div className="mt-8 flex flex-wrap gap-3 border-t border-border pt-8">
          <Link href={`/u/${encodeURIComponent(memory.host_username)}`}>
            <Button variant="secondary">More from host</Button>
          </Link>
          <Link href="/memories">
            <Button variant="secondary">All memories</Button>
          </Link>
        </div>
      </Container>
    </>
  );
}
