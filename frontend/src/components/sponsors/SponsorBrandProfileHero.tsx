import { headerDarkSurfaceProps } from "@/components/layout/headerSurface";
import { Badge, Button, Container } from "@/components/ui";
import { cn } from "@/lib/cn";
import { sponsorCoverAlt, sponsorLogoAlt } from "@/lib/seo/image-alt";
import Link from "next/link";
import type { ReactNode } from "react";

function sponsorInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export function SponsorBrandProfileHero({
  displayName,
  logoUrl,
  coverUrl,
  useCoverFallback,
  industry,
  sponsorTypeLabel,
  verified,
  shortBio,
  targetLocations,
  categories,
  actions,
  className,
}: {
  displayName: string;
  logoUrl: string | null;
  coverUrl: string | null;
  useCoverFallback: boolean;
  industry: string | null;
  sponsorTypeLabel?: string | null;
  verified: boolean;
  shortBio: string | null;
  targetLocations: string[];
  categories: string[];
  actions?: ReactNode;
  className?: string;
}) {
  const initials = sponsorInitials(displayName);
  const locationLine =
    targetLocations.length > 0
      ? targetLocations.slice(0, 3).join(" · ")
      : null;

  return (
    <section
      {...headerDarkSurfaceProps}
      className={cn("relative z-0 overflow-hidden bg-ink text-paper", className)}
    >
      <div className="absolute inset-0">
        {coverUrl && !useCoverFallback ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={coverUrl}
            alt={sponsorCoverAlt(displayName)}
            className="h-full w-full object-cover opacity-40 saturate-[0.9]"
          />
        ) : (
          <div
            aria-hidden
            className="flex h-full w-full flex-col items-center justify-center bg-gradient-to-br from-ink via-[#0f1410] to-ink"
          >
            <span className="select-none text-6xl font-black tracking-tight text-paper/10 sm:text-8xl">
              {initials}
            </span>
            {industry ? (
              <span className="mt-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent/80">
                {industry}
              </span>
            ) : null}
          </div>
        )}
      </div>
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink via-ink/70 to-ink/30"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -left-16 top-1/4 h-72 w-72 rounded-full bg-accent/20 blur-3xl"
      />

      <Container className="relative pb-12 pt-10 sm:pb-16 sm:pt-14">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end">
          {logoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={logoUrl}
              alt={sponsorLogoAlt(displayName)}
              className="h-24 w-24 shrink-0 rounded-2xl border-4 border-ink/80 bg-card object-cover shadow-lg sm:h-28 sm:w-28"
            />
          ) : (
            <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-2xl border-4 border-ink/80 bg-accent/20 text-xl font-bold text-paper shadow-lg sm:h-28 sm:w-28">
              {initials}
            </div>
          )}
          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="accent" className="uppercase tracking-[0.14em]">
                Sponsor partner
              </Badge>
              {verified ? (
                <Badge tone="success" className="uppercase tracking-[0.12em]">
                  Verified sponsor
                </Badge>
              ) : null}
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl md:text-[2.75rem]">
              {displayName}
            </h1>
            <p className="text-sm text-subtle-foreground sm:text-base">
              {[sponsorTypeLabel, industry].filter(Boolean).join(" · ")}
              {locationLine ? ` · ${locationLine}` : ""}
            </p>
            {shortBio ? (
              <p className="max-w-2xl text-base leading-relaxed text-subtle-foreground">
                {shortBio}
              </p>
            ) : null}
            {categories.length > 0 ? (
              <div className="flex flex-wrap gap-2 pt-1">
                {categories.map((c) => (
                  <span
                    key={c}
                    className="rounded-full border border-paper/15 bg-paper/5 px-3 py-1 text-xs font-medium capitalize text-paper/90"
                  >
                    {c.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            ) : null}
            {actions ? <div className="flex flex-wrap gap-3 pt-2">{actions}</div> : null}
          </div>
        </div>
      </Container>
    </section>
  );
}

export function SponsorBrandProfileHeroActions({
  showInquiry,
  websiteUrl,
  marketplaceHref,
  inquiryHref,
}: {
  showInquiry: boolean;
  websiteUrl: string | null;
  marketplaceHref: string;
  inquiryHref: string;
}) {
  return (
    <>
      {showInquiry ? (
        <Link href={inquiryHref}>
          <Button size="lg">Sponsor inquiry</Button>
        </Link>
      ) : null}
      <Link href={marketplaceHref}>
        <Button size="lg" variant="outline-dark">
          Browse sponsorship opportunities
        </Button>
      </Link>
      {websiteUrl ? (
        <a href={websiteUrl} target="_blank" rel="noopener noreferrer">
          <Button size="lg" variant="ghost" className="text-paper hover:bg-paper/10">
            Website
          </Button>
        </a>
      ) : null}
    </>
  );
}
