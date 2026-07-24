"use client";

import { Card, Media } from "@/components/ui";
import { formatDateTime, formatNgn } from "@/lib/format";

import { EventVisibilityBadge } from "./EventVisibilityBadge";
import { STUDIO_MEDIA_PLACEHOLDERS } from "./studio-media-placeholders";
import { refundPolicyLabel } from "./policy-utils";
import type { EventStudioValues } from "./types";

export function EventPreviewPanel({
  values,
  compact = false,
  onOpenFullPreview,
}: {
  values: EventStudioValues;
  /** Tighter layout for the mobile preview sheet */
  compact?: boolean;
  onOpenFullPreview?: () => void;
}) {
  const banner = values.banner_url || STUDIO_MEDIA_PLACEHOLDERS.banner;
  const when = values.start_datetime
    ? formatDateTime(new Date(values.start_datetime).toISOString())
    : "Date TBA";
  const ends = values.end_datetime
    ? formatDateTime(new Date(values.end_datetime).toISOString())
    : null;
  // Studio preview is privacy-safe: never show street address here.
  const location =
    values.location_visibility === "online_only"
      ? values.public_location_label || "Online Event"
      : values.public_location_label ||
        (values.location_visibility === "full_public"
          ? [values.venue_name, values.area || values.city, values.state]
              .filter(Boolean)
              .join(", ")
          : values.area || values.city) ||
        "Location details follow your privacy rules";
  const minTicket = values.ticket_drafts
    .map((t) => Number(t.price))
    .filter((n) => Number.isFinite(n));
  const priceLabel =
    minTicket.length === 0
      ? "Tickets TBA"
      : Math.min(...minTicket) === 0
        ? "Free RSVP available"
        : `From ${formatNgn(Math.min(...minTicket))}`;
  const descriptionPreview = values.description.trim()
    ? values.description.trim().slice(0, compact ? 160 : 220)
    : null;
  const lineup = values.people.filter((p) => p.name.trim()).slice(0, 4);
  const agenda = values.agenda_items.filter((a) => a.title.trim()).slice(0, 4);

  return (
    <aside className="space-y-4">
      <Card className="overflow-hidden border-border p-0 shadow-[var(--shadow)]">
        <div className="relative aspect-[16/10] bg-surface-dark">
          <Media src={banner} alt="" className="opacity-95" />
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink/85 via-ink/40 to-transparent p-4 pt-12">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-accent">
              Guest preview
            </p>
            <h3 className="mt-1.5 text-xl font-extrabold tracking-tight text-paper">
              {values.title || "Untitled event"}
            </h3>
            {values.short_tagline ? (
              <p className="mt-1 text-sm text-subtle-foreground">{values.short_tagline}</p>
            ) : (
              <p className="mt-1 text-sm text-subtle-foreground/80">
                Add a short tagline to sell the night
              </p>
            )}
          </div>
        </div>
        <div className="space-y-3 p-4">
          <div className="flex flex-wrap gap-2">
            <EventVisibilityBadge value={values.event_type} tone="accent" />
            <EventVisibilityBadge value={values.visibility} />
            <EventVisibilityBadge value={values.location_visibility} tone="warning" />
            {values.vibe ? <EventVisibilityBadge value={values.vibe} /> : null}
          </div>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">When</dt>
              <dd className="text-foreground">
                {when}
                {ends ? (
                  <span className="mt-0.5 block text-xs text-muted-foreground">Until {ends}</span>
                ) : null}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                Location
              </dt>
              <dd className="text-foreground">{location || "TBA"}</dd>
            </div>
            <div>
              <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                Tickets
              </dt>
              <dd className="text-foreground">{priceLabel}</dd>
            </div>
            {values.dress_code ? (
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                  Dress code
                </dt>
                <dd className="text-foreground">{values.dress_code}</dd>
              </div>
            ) : null}
            {values.refund_policy_type ? (
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                  Refunds
                </dt>
                <dd className="text-foreground">
                  {refundPolicyLabel(values.refund_policy_type)}
                </dd>
              </div>
            ) : null}
          </dl>
          {descriptionPreview ? (
            <p className="text-sm leading-relaxed text-muted-foreground">
              {descriptionPreview}
              {values.description.trim().length > descriptionPreview.length ? "…" : ""}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              Your description will appear here for guests browsing the event page.
            </p>
          )}
          {values.reveal_note || values.location_visibility !== "full_public" ? (
            <p className="rounded-[var(--radius-sm)] bg-muted px-3 py-2 text-xs leading-relaxed text-muted-foreground">
              {values.reveal_note ||
                "Exact venue is hidden on the public page until your reveal rule allows it."}
            </p>
          ) : null}
        </div>
      </Card>

      <Card className="space-y-2 border-border shadow-[var(--shadow-soft)]">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Ticket preview
        </p>
        {values.ticket_drafts.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Add ticket tiers in the Tickets step — guests will see prices here.
          </p>
        ) : (
          <ul className="space-y-2">
            {values.ticket_drafts.slice(0, 4).map((ticket) => (
              <li
                key={ticket.localId}
                className="flex items-center justify-between gap-2 border-b border-border pb-2 text-sm last:border-0"
              >
                <span className="font-medium text-foreground">
                  {ticket.name || "Untitled tier"}
                </span>
                <span className="text-muted-foreground">
                  {Number(ticket.price) === 0 ? "Free" : formatNgn(Number(ticket.price))}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {lineup.length > 0 ? (
        <Card className="space-y-2 border-border shadow-[var(--shadow-soft)]">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Lineup
          </p>
          <ul className="space-y-1.5 text-sm">
            {lineup.map((person, index) => (
              <li key={`preview-person-${index}`} className="text-foreground">
                <span className="font-medium">{person.name}</span>
                {person.role ? (
                  <span className="text-muted-foreground"> · {person.role}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {agenda.length > 0 ? (
        <Card className="space-y-2 border-border shadow-[var(--shadow-soft)]">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Agenda
          </p>
          <ul className="space-y-1.5 text-sm">
            {agenda.map((item, index) => (
              <li key={`preview-agenda-${index}`} className="text-foreground">
                <span className="font-medium">{item.title}</span>
                <span className="text-muted-foreground">
                  {" "}
                  · {item.type.replaceAll("_", " ")}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {(values.what_to_expect || values.what_to_bring) && !compact ? (
        <Card className="space-y-2 border-border shadow-[var(--shadow-soft)]">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Guest notes
          </p>
          {values.what_to_expect ? (
            <p className="text-sm text-foreground">
              <span className="font-semibold">Expect: </span>
              {values.what_to_expect.slice(0, 120)}
              {values.what_to_expect.length > 120 ? "…" : ""}
            </p>
          ) : null}
          {values.what_to_bring ? (
            <p className="text-sm text-foreground">
              <span className="font-semibold">Bring: </span>
              {values.what_to_bring.slice(0, 120)}
              {values.what_to_bring.length > 120 ? "…" : ""}
            </p>
          ) : null}
        </Card>
      ) : null}

      <p className="text-xs leading-relaxed text-muted-foreground">
        Quick glance while you edit. Use <span className="font-semibold text-foreground">Preview
        event page</span> to open the full guest listing in a new tab — same layout as a live
        event.
      </p>
      {onOpenFullPreview ? (
        <button
          type="button"
          onClick={onOpenFullPreview}
          className="text-xs font-bold uppercase tracking-wide text-foreground underline decoration-accent underline-offset-2"
        >
          Open full guest page
        </button>
      ) : null}
    </aside>
  );
}
