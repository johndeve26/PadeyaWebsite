"use client";

import Link from "next/link";
import { type ReactNode } from "react";

import { Badge, Button, Card, StatusBadge } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatNgn } from "@/lib/format";
import { formatCompactNumber } from "@/lib/sponsor-host-presentation";
import type { EnrichedSponsorshipSlot } from "@/lib/sponsor-slot-presentation";
import { sponsorshipMarketplaceUrl } from "@/lib/sponsor-marketplace-paths";
import type { SponsorshipSlot } from "@/lib/types/sponsorships";

function ProofChip({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center text-xs text-muted-foreground">
      {children}
    </span>
  );
}

export function SponsorSlotCard({
  slot,
  inquiryOpen = false,
  onToggleInquiry,
  inquiryForm,
  className = "",
  showModeration = false,
  actions,
  compact = false,
}: {
  slot: SponsorshipSlot | EnrichedSponsorshipSlot;
  inquiryOpen?: boolean;
  onToggleInquiry?: () => void;
  inquiryForm?: ReactNode;
  className?: string;
  showModeration?: boolean;
  actions?: ReactNode;
  /** Marketplace density — use on `/sponsorships` */
  compact?: boolean;
}) {
  const enriched = slot as EnrichedSponsorshipSlot;
  const city = enriched.city ?? null;
  const category = enriched.category ?? null;
  const audience =
    typeof enriched.audienceReach === "number" ? enriched.audienceReach : null;
  const hostHref = slot.host_username
    ? `/@${slot.host_username.replace(/^@/, "")}`
    : null;
  const slotsHref = slot.host_username
    ? sponsorshipMarketplaceUrl(slot.host_username)
    : null;

  if (!compact) {
    return (
      <Card hover={!inquiryOpen} className={cn("space-y-4", className)}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-xl font-extrabold tracking-tight text-foreground">
                {slot.title}
              </h3>
              <Badge tone="accent">{slot.slot_type_label}</Badge>
              {slot.host_verified ? <Badge tone="success">Verified host</Badge> : null}
              {showModeration ? <StatusBadge status={slot.moderation_status} /> : null}
              {showModeration ? <StatusBadge status={slot.status} /> : null}
            </div>
            <p className="text-sm text-muted-foreground">
              {slot.host_display_name}
              {slot.host_username ? (
                <>
                  {" "}
                  ·{" "}
                  <Link
                    href={`/@${slot.host_username}`}
                    className="font-semibold text-foreground underline-offset-2 hover:underline"
                  >
                    @{slot.host_username}
                  </Link>
                </>
              ) : null}
              {slot.event_title ? ` · ${slot.event_title}` : ""}
            </p>
          </div>
          <p className="shrink-0 rounded-[var(--radius-md)] bg-ink px-3 py-2 text-sm font-extrabold text-primary">
            {formatNgn(slot.price)}
          </p>
        </div>

        <p className="whitespace-pre-wrap text-sm leading-relaxed text-body">
          {slot.description}
        </p>

        {onToggleInquiry ? (
          <Button size="sm" onClick={onToggleInquiry}>
            {inquiryOpen ? "Hide inquiry form" : "Inquire"}
          </Button>
        ) : null}

        {inquiryOpen && inquiryForm ? (
          <div className="border-t border-border pt-4">{inquiryForm}</div>
        ) : null}

        {actions ? <div className="flex flex-wrap gap-2 pt-1">{actions}</div> : null}
      </Card>
    );
  }

  return (
    <article
      className={cn(
        "flex flex-col rounded-[var(--radius-lg)] border border-border bg-card px-4 py-3.5 shadow-[var(--shadow-soft)] transition-colors",
        "dark:bg-surface-elevated",
        inquiryOpen
          ? "border-primary/40"
          : "hover:border-primary/30 hover:shadow-[var(--shadow)]",
        "md:min-h-[140px] md:max-h-none",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <Badge tone="outline" className="max-w-[70%] truncate">
          {slot.slot_type_label}
        </Badge>
        <span className="shrink-0 text-sm font-extrabold text-foreground">
          {formatNgn(slot.price)}
        </span>
      </div>

      <div className="mt-2 min-w-0 space-y-1">
        <h3 className="truncate text-base font-extrabold tracking-tight text-foreground sm:text-lg">
          {slot.title}
        </h3>
        <p className="line-clamp-1 text-sm text-muted-foreground">
          {slot.description}
        </p>
        <p className="truncate text-sm text-muted-foreground">
          <span className="font-semibold text-foreground">
            {slot.host_display_name || "Host"}
          </span>
          {slot.host_username
            ? ` · @${slot.host_username.replace(/^@/, "")}`
            : ""}
          {slot.event_title ? ` · ${slot.event_title}` : ""}
        </p>
      </div>

      <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border/70 pt-2.5">
        {audience != null && audience > 0 ? (
          <ProofChip>{formatCompactNumber(audience)} reach</ProofChip>
        ) : null}
        {city ? <ProofChip>{city}</ProofChip> : null}
        {category ? <ProofChip>{category}</ProofChip> : null}
        <ProofChip>
          {slot.status === "published" ? "Available" : slot.status}
        </ProofChip>
        {slot.host_verified ? (
          <ProofChip>
            <span className="font-semibold text-accent">Verified</span>
          </ProofChip>
        ) : null}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {onToggleInquiry ? (
          <Button size="sm" onClick={onToggleInquiry}>
            {inquiryOpen ? "Close" : "Inquire"}
          </Button>
        ) : null}
        {hostHref ? (
          <Link href={hostHref}>
            <Button size="sm" variant="secondary">
              View host
            </Button>
          </Link>
        ) : null}
        {slotsHref && !hostHref ? (
          <Link href={slotsHref}>
            <Button size="sm" variant="ghost">
              View details
            </Button>
          </Link>
        ) : null}
        {actions}
      </div>

      {inquiryOpen && inquiryForm ? (
        <div className="mt-3 border-t border-border pt-3">{inquiryForm}</div>
      ) : null}
    </article>
  );
}
