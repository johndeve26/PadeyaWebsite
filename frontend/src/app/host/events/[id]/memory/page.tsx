"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Media,
  SectionHeader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchHostMemory } from "@/lib/memories-api";
import type { EventMemory } from "@/lib/types/memories";

export default function HostEventMemoryPage() {
  const params = useParams<{ id: string }>();
  const [memory, setMemory] = useState<EventMemory | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchHostMemory(params.id);
        if (active) setMemory(data);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Memory unavailable");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Event Memory"
        title={memory?.event_title ?? "Event Memory"}
        description="Public recap page for this completed event — stats, reviews, and gallery."
        actions={
          memory ? (
            <div className="flex flex-wrap gap-2">
              <Link href={`/host/events/${params.id}/memory/edit`}>
                <Button size="sm" variant="secondary">
                  Edit recap
                </Button>
              </Link>
              {memory.status === "published" ? (
                <Link href={memory.share_path}>
                  <Button size="sm">View public page</Button>
                </Link>
              ) : null}
            </div>
          ) : (
            <Link href={`/host/events/${params.id}`}>
              <Button size="sm" variant="ghost">
                Back to event
              </Button>
            </Link>
          )
        }
      >
        {error ? (
          <Alert tone="danger" title="Memory unavailable">
            {error}
          </Alert>
        ) : null}

        {memory ? (
          <div className="space-y-8">
            <div className="flex flex-wrap gap-2">
              <Badge tone={memory.status === "published" ? "success" : "neutral"}>
                {memory.status}
              </Badge>
              {memory.moderation_status !== "none" ? (
                <Badge tone="warning">Moderation: {memory.moderation_status}</Badge>
              ) : null}
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <StatCard
                title="Check-ins"
                value={memory.attendance.checked_in}
                hint={`of ${memory.attendance.tickets_sold} sold`}
              />
              <StatCard
                title="Verified rating"
                value={
                  memory.verified_rating != null
                    ? Number(memory.verified_rating).toFixed(1)
                    : "—"
                }
                hint={`${memory.review_count} reviews`}
              />
              <StatCard title="Gallery items" value={memory.media.length} />
            </div>

            <Card className="space-y-3">
              <SectionHeader title="Host thank-you note" />
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
                {memory.host_recap_note || "No recap note yet."}
              </p>
            </Card>

            <section className="space-y-4">
              <SectionHeader
                title={`Gallery (${memory.media.length})`}
                description="Photos and media shown on the public memory page."
              />
              {memory.media.length === 0 ? (
                <EmptyState
                  title="No media uploaded"
                  description="Add gallery images from the edit page."
                  action={
                    <Link href={`/host/events/${params.id}/memory/edit`}>
                      <Button size="sm">Edit recap</Button>
                    </Link>
                  }
                />
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {memory.media.map((m) => (
                    <Card key={m.id} padded={false} className="overflow-hidden">
                      <div className="relative aspect-[4/3] bg-surface-dark">
                        <Media
                          src={m.url}
                          alt={m.label ?? m.media_type}
                          className="h-full w-full object-cover"
                        />
                      </div>
                      <div className="space-y-1 p-3">
                        <p className="truncate text-sm font-semibold text-foreground">
                          {m.label || m.media_type}
                        </p>
                        <p className="truncate text-xs text-muted-foreground">{m.url}</p>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </section>

            <Alert tone="info" title="Public path">
              {memory.share_path}
            </Alert>
          </div>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
