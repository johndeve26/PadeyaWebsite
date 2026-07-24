"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { HostFollowControls } from "@/components/hosts/HostFollowControls";
import { SectionLabel } from "@/components/personal/command-center/SectionLabel";
import { Badge, Button, Card, EmptyState, SkeletonLoader } from "@/components/ui";
import {
  dismissHostRecommendation,
  fetchHostRecommendations,
  moreLikeHostRecommendation,
  notInterestedHostRecommendation,
  recordHostRecommendationClick,
  recordHostRecommendationFollow,
  recordHostRecommendationImpressions,
} from "@/lib/hosts-api";
import type { HostRecommendation } from "@/lib/types/hosts-discovery";

export type HostRecommendationSurface =
  | "dashboard_hosts_for_you"
  | "dashboard_overview"
  | "hosts_recommended_rail"
  | "hosts_sort_recommended";

type HostRecommendationsSectionProps = {
  variant?: "rail" | "page";
  limit?: number;
  surface?: HostRecommendationSurface;
  /** Rail title override (e.g. Recommended for you on /hosts). */
  title?: string;
  seeAllHref?: string | null;
};

export function HostRecommendationsSection({
  variant = "rail",
  limit = 6,
  surface = "dashboard_overview",
  title,
  seeAllHref = "/dashboard/hosts-for-you",
}: HostRecommendationsSectionProps) {
  const [items, setItems] = useState<HostRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [emptyCopy, setEmptyCopy] = useState<{
    title?: string | null;
    description?: string | null;
  }>({});
  const impressionsSent = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await fetchHostRecommendations({ limit });
      setItems(res.items);
      setEmptyCopy({
        title: res.empty_title,
        description: res.empty_description,
      });
    } catch {
      setError(true);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (loading || items.length === 0 || impressionsSent.current) return;
    impressionsSent.current = true;
    void recordHostRecommendationImpressions(
      items.map((item, index) => ({
        host_id: item.host.host_id,
        surface,
        position: index,
        recommendation_score: item.score,
        reason_codes: item.reasons.map((r) => r.code),
      })),
    ).catch(() => {
      impressionsSent.current = false;
    });
  }, [items, loading, surface]);

  async function onDismiss(hostId: string) {
    try {
      await dismissHostRecommendation(hostId);
      setItems((prev) => prev.filter((i) => i.host.host_id !== hostId));
    } catch {
      /* keep card */
    }
  }

  async function onNotInterested(hostId: string) {
    try {
      await notInterestedHostRecommendation(hostId);
      setItems((prev) => prev.filter((i) => i.host.host_id !== hostId));
    } catch {
      /* keep card */
    }
  }

  async function onMoreLike(hostId: string) {
    try {
      await moreLikeHostRecommendation(hostId);
    } catch {
      /* non-blocking */
    }
  }

  const railTitle = title ?? "Hosts for you";

  if (loading && variant === "rail") return null;

  if (loading && variant === "page") {
    return (
      <div className="space-y-3">
        <SkeletonLoader className="h-8 w-48" />
        <div className="grid gap-3 sm:grid-cols-2">
          <SkeletonLoader className="h-40" />
          <SkeletonLoader className="h-40" />
        </div>
      </div>
    );
  }

  if (error && variant === "rail") return null;

  if (error && variant === "page") {
    return (
      <EmptyState
        title="Couldn’t load recommendations"
        description="Try again in a moment."
        action={
          <Button size="sm" onClick={() => void load()}>
            Retry
          </Button>
        }
      />
    );
  }

  if (items.length === 0 && variant === "rail") return null;

  if (items.length === 0 && variant === "page") {
    return (
      <EmptyState
        title={emptyCopy.title ?? "No host matches yet"}
        description={
          emptyCopy.description ??
          "Follow hosts, buy tickets, or save your city in Connect settings and Pàdéyá will surface Legacy hosts that fit your nights."
        }
        action={
          <Link href="/hosts">
            <Button>Browse hosts</Button>
          </Link>
        }
      />
    );
  }

  return (
    <section className="min-w-0 space-y-3" data-surface={surface}>
      {variant === "rail" ? (
        <div className="flex flex-wrap items-end justify-between gap-2">
          <SectionLabel>{railTitle}</SectionLabel>
          {seeAllHref ? (
            <Link href={seeAllHref} className="text-sm font-semibold text-primary">
              See all
            </Link>
          ) : null}
        </div>
      ) : null}
      <div
        className={
          variant === "page"
            ? "grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-3"
            : "grid min-w-0 gap-3 sm:grid-cols-2"
        }
      >
        {items.map((item) => (
          <Card key={item.host.host_id} className="min-w-0 space-y-3 p-4">
            <div className="flex min-w-0 items-start justify-between gap-2">
              <div className="min-w-0">
                <Link
                  href={item.host.share_path}
                  className="font-extrabold text-foreground hover:text-primary"
                  onClick={() => void recordHostRecommendationClick(item.host.host_id)}
                >
                  {item.host.display_name}
                </Link>
                <p className="text-sm text-muted-foreground">
                  @{item.host.username}
                  {item.host.primary_city ? ` · ${item.host.primary_city}` : ""}
                </p>
              </div>
              {item.recommendation_label ? (
                <Badge tone="accent" className="shrink-0 text-xs">
                  {item.recommendation_label}
                </Badge>
              ) : null}
            </div>
            {item.reasons.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {item.reasons.slice(0, 3).map((r) => (
                  <Badge key={r.code} tone="neutral" className="text-xs font-normal">
                    {r.label}
                  </Badge>
                ))}
              </div>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Link href={item.host.share_path}>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => void recordHostRecommendationClick(item.host.host_id)}
                >
                  View Host
                </Button>
              </Link>
              <Link href={`${item.host.share_path}/events`}>
                <Button size="sm" variant="ghost">
                  View Events
                </Button>
              </Link>
              <HostFollowControls
                hostId={item.host.host_id}
                hostSlug={item.host.username}
                hostDisplayName={item.host.display_name}
                loginNextPath="/hosts"
                size="sm"
                promptAfterFollow={false}
                onBeforeFollowToggle={() => {
                  void recordHostRecommendationFollow(item.host.host_id);
                }}
              />
              <Button
                size="sm"
                variant="ghost"
                onClick={() => void onMoreLike(item.host.host_id)}
              >
                More like this
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => void onDismiss(item.host.host_id)}
              >
                Dismiss
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => void onNotInterested(item.host.host_id)}
              >
                Not interested
              </Button>
            </div>
          </Card>
        ))}
      </div>
      {variant === "page" ? (
        <p className="text-sm text-muted-foreground">
          <Link href="/hosts" className="font-semibold text-primary">
            Browse the full host marketplace
          </Link>{" "}
          for the global directory.
        </p>
      ) : null}
    </section>
  );
}
