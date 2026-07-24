import Link from "next/link";

import { Badge, Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatDate } from "@/lib/format";
import type {
  SponsorPublicCampaignCard,
  SponsorPublicPartnerHost,
  SponsorPublicRelatedSponsor,
  SponsorPublicSponsoredEvent,
} from "@/lib/sponsor-profiles-api";

const cardShell =
  "rounded-[var(--radius-lg)] border border-border border-l-4 border-l-primary/70 bg-card p-5 shadow-sm transition hover:border-primary/30";

export function SponsorPublicCampaignCardView({
  campaign,
}: {
  campaign: SponsorPublicCampaignCard;
}) {
  return (
    <article className={cn(cardShell, "flex h-full flex-col gap-3")}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-lg font-bold text-foreground">{campaign.name}</h3>
        <Badge tone="neutral">{campaign.status_label}</Badge>
      </div>
      <p className="text-sm font-medium text-primary">{campaign.objective_label}</p>
      {campaign.description ? (
        <p className="text-sm leading-relaxed text-muted-foreground">
          {campaign.description}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {campaign.target_categories.map((cat) => (
          <span
            key={cat}
            className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium capitalize text-foreground"
          >
            {cat.replace(/_/g, " ")}
          </span>
        ))}
      </div>
      {campaign.target_locations.length > 0 ? (
        <p className="text-xs text-muted-foreground">
          Locations: {campaign.target_locations.join(" · ")}
        </p>
      ) : null}
      <div className="mt-auto flex flex-wrap items-center justify-between gap-3 pt-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {campaign.linked_sponsored_events_count > 0
            ? `${campaign.linked_sponsored_events_count} linked placement${
                campaign.linked_sponsored_events_count === 1 ? "" : "s"
              }`
            : "Public case study"}
        </p>
        {campaign.linked_sponsored_events_count > 0 ? (
          <Link href="#sponsored-events-placements">
            <Button variant="ghost" size="sm">
              View related events
            </Button>
          </Link>
        ) : null}
      </div>
    </article>
  );
}

export function SponsorPublicSponsoredEventCard({
  event: ev,
}: {
  event: SponsorPublicSponsoredEvent;
}) {
  const location = ev.area || ev.city;
  return (
    <article className={cn(cardShell, "flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between")}>
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          {ev.category ? (
            <Badge tone="accent" className="capitalize">
              {ev.category}
            </Badge>
          ) : null}
          <Badge tone={ev.placement_status === "active" ? "success" : "neutral"}>
            {ev.placement_status === "active" ? "Active" : "Completed"}
          </Badge>
        </div>
        <h3 className="text-lg font-bold text-foreground">
          {ev.event_slug ? (
            <Link href={`/events/${ev.event_slug}`} className="hover:text-primary">
              {ev.event_title}
            </Link>
          ) : (
            ev.event_title
          )}
        </h3>
        <p className="text-sm text-muted-foreground">
          {ev.host_display_name}
          {ev.host_verified ? " · Verified host" : ""}
          {location ? ` · ${location}` : ""}
          {ev.starts_at ? ` · ${formatDate(ev.starts_at)}` : ""}
        </p>
        {ev.deliverable_labels.length > 0 ? (
          <div className="flex flex-wrap gap-2 pt-1">
            {ev.deliverable_labels.slice(0, 4).map((d) => (
              <span
                key={d}
                className="rounded-md border border-primary/20 bg-primary/5 px-2 py-1 text-xs font-medium text-foreground"
              >
                {d}
              </span>
            ))}
          </div>
        ) : null}
      </div>
      <div className="flex shrink-0 flex-wrap gap-2 lg:flex-col lg:items-stretch">
        {ev.event_slug ? (
          <Link href={`/events/${ev.event_slug}`}>
            <Button size="sm" className="w-full min-w-[8rem]">
              View event
            </Button>
          </Link>
        ) : null}
        {ev.host_slug ? (
          <Link href={`/u/${ev.host_slug}`}>
            <Button variant="secondary" size="sm" className="w-full min-w-[8rem]">
              View host
            </Button>
          </Link>
        ) : null}
      </div>
    </article>
  );
}

export function SponsorPublicPartnerHostCard({ host: h }: { host: SponsorPublicPartnerHost }) {
  return (
    <article className={cn(cardShell, "flex h-full flex-col gap-3")}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-lg font-bold text-foreground">{h.display_name}</p>
          {h.city ? <p className="text-sm text-muted-foreground">{h.city}</p> : null}
        </div>
        {h.verified ? (
          <Badge tone="success" className="shrink-0">
            Verified
          </Badge>
        ) : null}
      </div>
      {h.sponsored_events_together > 0 ? (
        <p className="text-sm font-medium text-foreground">
          Sponsored {h.sponsored_events_together} event
          {h.sponsored_events_together === 1 ? "" : "s"} together
        </p>
      ) : null}
      {h.categories.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {h.categories.map((c) => (
            <span
              key={c}
              className="rounded-full bg-muted px-2 py-0.5 text-xs capitalize text-muted-foreground"
            >
              {c}
            </span>
          ))}
        </div>
      ) : null}
      {h.slug ? (
        <Link href={`/u/${h.slug}`} className="mt-auto pt-1">
          <Button variant="secondary" size="sm">
            View host
          </Button>
        </Link>
      ) : null}
    </article>
  );
}

export function SponsorPublicRelatedSponsorCard({
  sponsor: s,
}: {
  sponsor: SponsorPublicRelatedSponsor;
}) {
  return (
    <Link
      href={`/sponsors/${s.slug}`}
      className={cn(cardShell, "block hover:bg-muted/20")}
    >
      <div className="flex items-start gap-3">
        {s.logo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={s.logo_url} alt="" className="h-12 w-12 rounded-lg object-cover" />
        ) : (
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/15 text-sm font-bold text-primary">
            {s.display_name.slice(0, 2).toUpperCase()}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="font-bold text-foreground">{s.display_name}</p>
          {s.industry ? (
            <p className="text-sm text-muted-foreground">{s.industry}</p>
          ) : null}
          {s.categories.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-1">
              {s.categories.slice(0, 3).map((c) => (
                <span
                  key={c}
                  className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-foreground"
                >
                  {c}
                </span>
              ))}
            </div>
          ) : null}
          <p className="mt-3 text-xs font-semibold text-primary">View sponsor →</p>
        </div>
      </div>
    </Link>
  );
}
