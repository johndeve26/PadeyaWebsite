"use client";

import Link from "next/link";

import { HostSponsorCard } from "./HostSponsorCard";
import { Button, SectionHeader } from "@/components/ui";
import { SPONSORSHIP_HOSTS_PATH } from "@/lib/sponsor-marketplace-paths";
import type { SponsorHostPresentation } from "@/lib/sponsor-host-presentation";

export function FeaturedSponsorHosts({
  hosts,
}: {
  hosts: SponsorHostPresentation[];
}) {
  if (hosts.length === 0) return null;

  const [primary, ...rest] = hosts;
  const sideHosts = rest.slice(0, 2);

  return (
    <section className="space-y-6">
      <SectionHeader
        eyebrow="Featured hosts"
        title="Creators brands inquire about first"
        description="Verified hosts with Legacy, audience proof, and active sponsor packages."
        action={
          <Link href={SPONSORSHIP_HOSTS_PATH}>
            <Button variant="secondary">All hosts</Button>
          </Link>
        }
      />

      {/* Mobile: single column */}
      <div className="grid gap-4 md:hidden">
        {hosts.slice(0, 3).map((host) => (
          <HostSponsorCard
            key={host.host_id}
            host={host}
            featured={host.featured}
            layout="stack"
          />
        ))}
      </div>

      {/* Desktop: one large + two stacked */}
      <div className="hidden gap-4 md:grid md:grid-cols-2 md:items-stretch lg:grid-cols-[1.15fr_0.85fr]">
        <HostSponsorCard
          host={primary}
          featured
          layout="hero"
          className="min-h-full"
        />
        <div className="flex min-h-0 flex-col gap-4">
          {sideHosts.map((host) => (
            <HostSponsorCard
              key={host.host_id}
              host={host}
              featured={false}
              layout="side"
              className="min-h-0 flex-1"
            />
          ))}
          {sideHosts.length === 0 ? (
            <div className="flex flex-1 items-center justify-center rounded-[var(--radius-xl)] border border-dashed border-border bg-muted/50 p-6 text-sm text-muted-foreground">
              More verified hosts appear as packages go live.
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
