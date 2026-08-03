"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Button, SectionHeader } from "@/components/ui";
import { enlargeableAttrs } from "@/components/media/ImageLightbox";
import { cn } from "@/lib/cn";

export type FollowedHostCard = {
  host_id: string;
  display_name: string;
  username: string;
  share_path?: string | null;
  avatar_url?: string | null;
  city?: string | null;
  category?: string | null;
  is_verified?: boolean;
  legacy_tier?: string | null;
};

type Props = {
  hosts: FollowedHostCard[];
  initialVisible?: number;
};

function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "H";
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

export function FollowedHostCards({ hosts, initialVisible = 6 }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (hosts.length === 0) return null;

  const visible = expanded ? hosts : hosts.slice(0, initialVisible);

  return (
    <section className="space-y-4">
      <SectionHeader
        eyebrow="Hosts"
        title="Hosts this fan follows"
        description="Creators this fan keeps up with on Pàdéyá."
      />
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {visible.map((h) => {
          const href = h.share_path || (h.username ? `/@${h.username}` : "#");
          return (
            <li key={h.host_id}>
              <article className="flex h-full flex-col rounded-[var(--radius-lg)] border border-border bg-card p-4 shadow-[var(--shadow-soft)]">
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      "flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-full",
                      "bg-ink text-sm font-extrabold text-primary ring-1 ring-border",
                    )}
                  >
                    {h.avatar_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={h.avatar_url}
                        alt={h.display_name}
                        className="h-full w-full cursor-zoom-in object-cover"
                        {...enlargeableAttrs(h.avatar_url, h.display_name)}
                      />
                    ) : (
                      initials(h.display_name)
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <h3 className="truncate text-base font-extrabold text-foreground">
                        {h.display_name}
                      </h3>
                      {h.is_verified ? (
                        <Badge tone="accent" size="sm">
                          Verified
                        </Badge>
                      ) : null}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      @{h.username}
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {h.legacy_tier ? (
                    <Badge tone="outline" size="sm">
                      {h.legacy_tier}
                    </Badge>
                  ) : null}
                  {h.category ? (
                    <Badge tone="neutral" size="sm">
                      {h.category}
                    </Badge>
                  ) : null}
                  {h.city ? (
                    <Badge tone="outline" size="sm">
                      {h.city}
                    </Badge>
                  ) : null}
                </div>
                <div className="mt-auto pt-4">
                  <Link href={href}>
                    <Button size="sm" variant="primary" className="w-full">
                      View Legacy
                    </Button>
                  </Link>
                </div>
              </article>
            </li>
          );
        })}
      </ul>
      {hosts.length > initialVisible ? (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Show less" : `Show more (${hosts.length})`}
        </Button>
      ) : null}
    </section>
  );
}
