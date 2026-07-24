"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  Badge,
  Button,
  Card,
  Container,
  EmptyState,
  Media,
  ReviewCard,
  SkeletonLoader,
} from "@/components/ui";
import { RelatedVaultTeaserSection } from "@/components/vault/public/RelatedVaultTeaserSection";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { fetchPublicMemory } from "@/lib/memories-api";
import type { EventMemory } from "@/lib/types/memories";
import type { VaultCatalogCard } from "@/lib/types/vault";
import { fetchVaultRelatedToMemory } from "@/lib/vault-api";

export default function PublicEventMemoryPage() {
  const params = useParams<{ username: string; eventSlug: string }>();
  const username = decodeURIComponent(params.username);
  const eventSlug = decodeURIComponent(params.eventSlug);
  const [memory, setMemory] = useState<EventMemory | null>(null);
  const [relatedVault, setRelatedVault] = useState<VaultCatalogCard[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchPublicMemory(username, eventSlug);
        if (!active) return;
        setMemory(data);
        const vault = await fetchVaultRelatedToMemory(data.id).catch(
          () => [] as VaultCatalogCard[],
        );
        if (active) setRelatedVault(vault);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Memory not found");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [username, eventSlug]);

  if (error) {
    return (
      <main className="min-h-screen bg-card py-16">
        <Container width="narrow">
          <EmptyState
            title="Memory unavailable"
            description={error}
            action={
              <Link href={`/@${username}`}>
                <Button variant="secondary">Back to Legacy Page</Button>
              </Link>
            }
          />
        </Container>
      </main>
    );
  }

  if (!memory) {
    return (
      <main className="min-h-screen bg-card py-16">
        <Container width="narrow">
          <SkeletonLoader lines={6} />
        </Container>
      </main>
    );
  }

  const rating =
    memory.verified_rating != null ? Number(memory.verified_rating).toFixed(1) : null;

  return (
    <main className="min-h-screen bg-card">
      <section className="relative min-h-[42vh] overflow-hidden bg-ink text-paper">
        {memory.banner_url ? (
          <div className="absolute inset-0">
            <Media src={memory.banner_url} className="opacity-75" />
            <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/70 to-ink/30" />
          </div>
        ) : (
          <div aria-hidden className="padeya-hero-glow absolute inset-0" />
        )}
        <Container className="relative flex min-h-[42vh] flex-col justify-end gap-3 py-12">
          <Badge tone="accent">Event Memory</Badge>
          <h1 className="max-w-3xl text-4xl font-extrabold tracking-tight md:text-5xl">
            {memory.event_title}
          </h1>
          <p className="text-sm text-subtle-foreground">
            {formatDateTime(memory.start_datetime)}
            {memory.venue_name ? ` · ${memory.venue_name}` : ""}
            {memory.city ? ` · ${memory.city}` : ""}
          </p>
          <Link
            href={`/@${memory.host_username}`}
            className="text-sm font-semibold text-paper underline decoration-paper/40 underline-offset-4"
          >
            Hosted by {memory.host_display_name}
          </Link>
        </Container>
      </section>

      <Container className="space-y-14 py-12">
        <section className="grid gap-3 sm:grid-cols-3">
          {[
            ["Verified check-ins", memory.attendance.checked_in],
            ["Tickets sold", memory.attendance.tickets_sold],
            ["Verified rating", rating ?? "—"],
          ].map(([label, value]) => (
            <Card key={String(label)} className="space-y-1 padeya-stat-surface">
              <p className="text-2xl font-extrabold tracking-tight">{value}</p>
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                {label}
              </p>
            </Card>
          ))}
        </section>

        {memory.host_recap_note ? (
          <section className="max-w-3xl space-y-3">
            <h2 className="text-2xl font-extrabold tracking-tight">From the host</h2>
            <p className="whitespace-pre-wrap leading-relaxed text-muted-foreground">
              {memory.host_recap_note}
            </p>
          </section>
        ) : null}

        <section className="space-y-4">
          <h2 className="text-2xl font-extrabold tracking-tight">Gallery</h2>
          {memory.media.length === 0 ? (
            <EmptyState title="No gallery media yet" />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {memory.media.map((m) => (
                <figure
                  key={m.id}
                  className="overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card shadow-[var(--shadow-soft)]"
                >
                  <div className="aspect-[4/3] bg-surface-dark">
                    <Media src={m.url} alt={m.label || memory.event_title} />
                  </div>
                  {m.label ? (
                    <figcaption className="px-4 py-3 text-sm text-muted-foreground">
                      {m.label}
                    </figcaption>
                  ) : null}
                </figure>
              ))}
            </div>
          )}
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-extrabold tracking-tight">Top verified reviews</h2>
          {memory.top_reviews.length === 0 ? (
            <EmptyState title="No verified reviews for this event yet" />
          ) : (
            <div className="space-y-4">
              {memory.top_reviews.map((review) => (
                <ReviewCard
                  key={review.id}
                  rating={review.rating}
                  title={review.title}
                  body={review.body}
                  reviewerName={review.reviewer_name}
                />
              ))}
            </div>
          )}
        </section>

        <RelatedVaultTeaserSection
          items={relatedVault}
          username={memory.host_username}
          hostId={memory.host_id}
          sourcePage="event_memory"
          listContext="event_memory"
          title="Full recap in Vault"
          description="Watch the full recap in Vault — exclusive drops tied to this night."
          vaultHref={`/u/${memory.host_username}/vault`}
          ctaLabel="Open Vault"
        />

        <section className="space-y-4">
          <h2 className="text-2xl font-extrabold tracking-tight">What&apos;s next</h2>
          {memory.upcoming_events.length === 0 ? (
            <EmptyState
              title="No upcoming events right now"
              description="Visit the host’s Legacy Page for more."
              action={
                <Link href={`/@${memory.host_username}`}>
                  <Button variant="secondary">Legacy Page</Button>
                </Link>
              }
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {memory.upcoming_events.map((event) => (
                <Link key={event.id} href={`/events/${event.slug}`} className="group">
                  <Card hover className="space-y-2">
                    <p className="font-bold group-hover:underline">{event.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatDateTime(event.start_datetime)}
                      {event.city ? ` · ${event.city}` : ""}
                    </p>
                    <span className="inline-block pt-1">
                      <Button size="sm">Get tickets</Button>
                    </span>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </section>
      </Container>
    </main>
  );
}
