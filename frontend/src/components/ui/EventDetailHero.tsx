import { type ReactNode } from "react";

import { cn } from "@/lib/cn";
import { formatPublicPlaceLabel } from "@/lib/event-privacy";
import type { EventItem } from "@/lib/types/events";
import { headerDarkSurfaceProps } from "@/components/layout/headerSurface";

import { Badge } from "./Badge";
import { Container } from "./Container";
import { Media } from "./Media";

export function EventDetailHero({
  event,
  actions,
  className = "",
}: {
  event: EventItem;
  actions?: ReactNode;
  className?: string;
}) {
  const when = new Date(event.start_datetime).toLocaleString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
  const place = formatPublicPlaceLabel(event) || "Location TBA";

  return (
    <section
      {...headerDarkSurfaceProps}
      className={cn(
        "relative min-h-[42vh] overflow-hidden bg-ink text-paper sm:min-h-[52vh]",
        className,
      )}
    >
      {event.banner_url ? (
        <div className="absolute inset-0">
          <Media
            src={event.banner_url}
            alt=""
            className="padeya-hero-media h-full w-full object-cover opacity-70"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/70 to-ink/30" />
        </div>
      ) : (
        <div aria-hidden className="padeya-hero-glow absolute inset-0" />
      )}
      <Container className="relative flex min-h-[42vh] flex-col justify-end gap-4 py-10 sm:min-h-[52vh] sm:py-14">
        <div className="flex flex-wrap gap-2">
          {event.featured ? <Badge tone="accent">Featured</Badge> : null}
          {event.category ? <Badge tone="dark">{event.category.name}</Badge> : null}
        </div>
        <h1 className="max-w-3xl text-balance break-words text-2xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl">
          {event.title}
        </h1>
        {event.short_tagline ? (
          <p className="max-w-2xl text-base text-paper/80 sm:text-lg">{event.short_tagline}</p>
        ) : null}
        <p className="max-w-2xl text-sm text-paper/75 sm:text-base">{when}</p>
        <p className="text-sm text-paper/75">{place}</p>
        <p className="text-sm text-paper/75">
          Hosted by{" "}
          <span className="font-semibold text-paper">
            {event.host_display_name ?? "Pàdéyá host"}
          </span>
        </p>
        {actions ? <div className="flex flex-wrap gap-2 pt-1">{actions}</div> : null}
      </Container>
    </section>
  );
}
