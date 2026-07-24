"use client";

import Link from "next/link";

import { Badge, Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { SponsorDirectoryCard } from "@/lib/sponsor-profiles-api";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

const SPONSOR_TYPE_LABELS: Record<string, string> = {
  brand: "Brand",
  business: "Business",
  agency: "Agency",
  media_partner: "Media partner",
  community: "Community",
};

export function SponsorDirectoryCardView({ sponsor: s }: { sponsor: SponsorDirectoryCard }) {
  const showLogo = s.logo_url && !s.use_logo_fallback;

  return (
    <li
      className={cn(
        "flex h-full flex-col rounded-[var(--radius-lg)] border border-border border-l-4 border-l-primary/70",
        "bg-card p-5 shadow-sm transition hover:border-primary/40 hover:shadow-md",
      )}
    >
      <div className="flex items-start gap-3">
        {showLogo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={s.logo_url!}
            alt=""
            className="h-14 w-14 shrink-0 rounded-xl border border-border object-cover"
          />
        ) : (
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-base font-bold text-primary">
            {initials(s.display_name)}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-lg font-bold leading-tight text-foreground">
              {s.display_name}
            </p>
            {s.verified ? (
              <Badge tone="success" className="text-[10px] uppercase tracking-wide">
                Verified
              </Badge>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {[s.industry, s.sponsor_type ? SPONSOR_TYPE_LABELS[s.sponsor_type] ?? s.sponsor_type : null]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
      </div>

      {s.short_bio ? (
        <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
          {s.short_bio}
        </p>
      ) : null}

      {s.categories.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {s.categories.slice(0, 4).map((cat) => (
            <span
              key={cat}
              className="rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-medium capitalize text-foreground"
            >
              {cat.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      ) : null}

      {s.target_locations.length > 0 ? (
        <p className="mt-2 text-xs text-muted-foreground">
          {s.target_locations.slice(0, 2).join(" · ")}
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {s.sponsored_events_count > 0 ? (
          <span className="rounded-md bg-muted px-2 py-1">
            {s.sponsored_events_count} event{s.sponsored_events_count === 1 ? "" : "s"}
          </span>
        ) : null}
        {s.public_campaigns_count > 0 ? (
          <span className="rounded-md bg-muted px-2 py-1">
            {s.public_campaigns_count} case stud{s.public_campaigns_count === 1 ? "y" : "ies"}
          </span>
        ) : null}
        {s.partnered_hosts_count > 0 ? (
          <span className="rounded-md bg-muted px-2 py-1">
            {s.partnered_hosts_count} host{s.partnered_hosts_count === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>

      {s.partnership_hint ? (
        <p className="mt-2 text-xs font-medium text-foreground/80">{s.partnership_hint}</p>
      ) : null}

      {s.accepting_inquiries ? (
        <p className="mt-2 text-xs font-semibold text-primary">Accepting inquiries</p>
      ) : null}

      <div className="mt-auto flex flex-wrap gap-2 pt-4">
        <Link href={`/sponsors/${s.slug}`} className="flex-1 sm:flex-none">
          <Button size="sm" className="w-full sm:w-auto">
            View partnership profile
          </Button>
        </Link>
      </div>
    </li>
  );
}
