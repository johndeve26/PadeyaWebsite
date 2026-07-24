import Link from "next/link";

import { SponsorSaveButton } from "@/components/sponsor/SponsorSaveButton";
import { Badge, Button, LegacyTierBadge, Media } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  formatCompactNumber,
  type SponsorHostPresentation,
} from "@/lib/sponsor-host-presentation";
import { sponsorshipMarketplaceUrl } from "@/lib/sponsor-marketplace-paths";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-[var(--radius-sm)] bg-surface-elevated px-2 py-1.5 shadow-[var(--shadow-soft)]">
      <p className="truncate text-sm font-extrabold text-heading">{value}</p>
      <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
        {label}
      </p>
    </div>
  );
}

export function HostSponsorCard({
  host,
  featured = false,
  layout = "stack",
  className = "",
}: {
  host: SponsorHostPresentation;
  featured?: boolean;
  /** hero = large featured; side = compact stacked; stack = marketplace grid */
  layout?: "hero" | "side" | "stack";
  className?: string;
}) {
  const isHero = layout === "hero" || (featured && layout === "stack");
  const isSide = layout === "side";
  const bio = host.pitch || host.bio || "Verified host open to brand partnerships.";

  return (
    <article
      className={cn(
        "group flex h-full flex-col overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow)] transition-all duration-200",
        "dark:bg-surface-elevated",
        "hover:-translate-y-1 hover:border-primary/40 hover:shadow-[var(--shadow-glow)]",
        className,
      )}
    >
      <div
        className={cn(
          "relative overflow-hidden bg-surface-dark",
          isHero && "aspect-[2.1/1] min-h-[180px] sm:min-h-[220px]",
          isSide && "aspect-[21/9] min-h-[100px] max-h-[120px]",
          layout === "stack" && !isHero && "aspect-[16/10] min-h-[160px]",
        )}
      >
        {host.coverUrl ? (
          <Media
            src={host.coverUrl}
            alt={`${host.display_name} cover`}
            className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-surface-dark via-dark-gray to-ink">
            <div className="padeya-hero-glow absolute inset-0 opacity-70" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/30 to-transparent" />
        <div className="absolute left-3 top-3 flex flex-wrap gap-2">
          {host.verified ? <Badge tone="dark">Verified</Badge> : null}
          {host.category ? (
            <Badge tone="outline" className="border-paper/30 bg-ink/40 text-paper">
              {host.category}
            </Badge>
          ) : null}
        </div>
        <div className="absolute bottom-3 left-3 right-3 flex items-end gap-3">
          <div
            className={cn(
              "relative shrink-0 overflow-hidden rounded-full border-2 border-accent bg-surface-dark shadow-[var(--shadow)]",
              isSide ? "h-12 w-12" : "h-14 w-14 sm:h-16 sm:w-16",
            )}
          >
            {host.avatarUrl ? (
              <Media
                src={host.avatarUrl}
                alt=""
                className="h-full w-full object-cover"
              />
            ) : (
              <span className="flex h-full w-full items-center justify-center text-lg font-extrabold text-primary">
                {host.display_name.slice(0, 1).toUpperCase()}
              </span>
            )}
          </div>
          <div className="min-w-0 flex-1 pb-0.5">
            <div className="flex flex-wrap items-center gap-2">
              <h3
                className={cn(
                  "truncate font-extrabold text-paper [text-shadow:0_2px_12px_rgb(0_0_0_/_0.65)]",
                  isHero ? "text-2xl sm:text-3xl" : "text-lg sm:text-xl",
                )}
              >
                {host.display_name}
              </h3>
              {host.tier ? <LegacyTierBadge tier={host.tier} /> : null}
            </div>
            <p className="truncate text-sm font-medium text-paper/75">
              @{host.username.replace(/^@/, "")}
              {host.city ? ` · ${host.city}` : ""}
            </p>
          </div>
        </div>
      </div>

      <div
        className={cn(
          "flex flex-1 flex-col gap-3 p-4",
          isHero && "sm:gap-4 sm:p-5",
          isSide && "gap-2.5 p-3.5",
        )}
      >
        <p
          className={cn(
            "leading-relaxed text-muted-foreground",
            isHero ? "line-clamp-3 text-sm sm:text-base" : "line-clamp-2 text-sm",
            isSide && "line-clamp-1 text-xs sm:text-sm",
          )}
        >
          {bio}
        </p>

        <div
          className={cn(
            "grid gap-1.5 rounded-[var(--radius-md)] border border-border bg-muted p-1.5",
            isHero ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-2 sm:grid-cols-4",
            isSide && "grid-cols-4",
          )}
        >
          <Stat label="Slots" value={String(host.open_slots)} />
          <Stat
            label="Audience"
            value={formatCompactNumber(host.verifiedCheckins || host.followers)}
          />
          <Stat label="Events" value={formatCompactNumber(host.eventsHosted)} />
          <Stat
            label="Rating"
            value={
              host.averageRating != null
                ? host.averageRating.toFixed(1)
                : "—"
            }
          />
        </div>

        <div
          className={cn(
            "mt-auto flex flex-col gap-2 pt-0.5",
            isSide ? "sm:flex-row" : "sm:flex-row",
          )}
        >
          <SponsorSaveButton itemType="host" itemId={host.host_id} className="w-full sm:w-auto" />
          <Link
            href={sponsorshipMarketplaceUrl(host.username)}
            className="sm:flex-1"
          >
            <Button size={isSide ? "sm" : "lg"} className="w-full">
              View sponsor slots
            </Button>
          </Link>
          <Link
            href={`/@${host.username.replace(/^@/, "")}`}
            className="sm:flex-1"
          >
            <Button
              size={isSide ? "sm" : "lg"}
              variant="secondary"
              className="w-full"
            >
              Legacy Page
            </Button>
          </Link>
        </div>
      </div>
    </article>
  );
}
