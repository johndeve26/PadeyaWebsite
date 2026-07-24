"use client";

import Link from "next/link";

import { useHeaderAccess } from "@/components/layout/HeaderWorkspaceButton";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  SponsorBrandProfileHero,
  SponsorBrandProfileHeroActions,
} from "@/components/sponsors/SponsorBrandProfileHero";
import {
  Button,
  Container,
  EmptyState,
  SectionHeader,
} from "@/components/ui";
import {
  SPONSORSHIP_MARKETPLACE_PATH,
  SPONSORSHIP_OPEN_SLOTS_HASH,
} from "@/lib/sponsor-marketplace-paths";
import type { SponsorPublicProfile } from "@/lib/sponsor-profiles-api";
import {
  SponsorPublicCampaignCardView,
  SponsorPublicPartnerHostCard,
  SponsorPublicRelatedSponsorCard,
  SponsorPublicSponsoredEventCard,
} from "@/components/sponsors/SponsorPublicProfileCards";

function SectionEmpty({ title, body }: { title: string; body: string }) {
  return (
    <EmptyState
      title={title}
      description={body}
      className="border border-dashed border-border bg-muted/30 py-10"
    />
  );
}

function ChipRow({ items, label }: { items: string[]; label: string }) {
  if (items.length === 0) return null;
  return (
    <div className="space-y-3">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </p>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <span
            key={item}
            className="rounded-full border border-border bg-card px-3 py-1.5 text-sm capitalize text-foreground shadow-sm"
          >
            {item.replace(/_/g, " ")}
          </span>
        ))}
      </div>
    </div>
  );
}

export function PublicSponsorProfileView({ profile }: { profile: SponsorPublicProfile }) {
  const { user } = useAuth();
  const { hasHostWorkspace } = useHeaderAccess(user, false);

  const marketplaceHref = `${SPONSORSHIP_MARKETPLACE_PATH}${SPONSORSHIP_OPEN_SLOTS_HASH}`;
  const inquiryHref = `${SPONSORSHIP_MARKETPLACE_PATH}?sponsor=${encodeURIComponent(profile.slug)}${SPONSORSHIP_OPEN_SLOTS_HASH}`;
  const sponsorTypeCard = profile.summary_cards.find((c) => c.label === "Sponsor type");

  return (
    <main className="min-h-screen bg-background">
      <SponsorBrandProfileHero
        displayName={profile.display_name}
        logoUrl={profile.logo_url}
        coverUrl={profile.cover_image_url}
        useCoverFallback={profile.use_cover_fallback}
        industry={profile.industry}
        sponsorTypeLabel={sponsorTypeCard?.value ?? profile.sponsor_type}
        verified={profile.verified}
        shortBio={profile.short_bio}
        targetLocations={profile.target_locations}
        categories={profile.categories}
        actions={
          <SponsorBrandProfileHeroActions
            showInquiry={profile.show_contact_cta}
            websiteUrl={profile.website_url}
            marketplaceHref={marketplaceHref}
            inquiryHref={inquiryHref}
          />
        }
      />

      <Container className="space-y-14 py-10 sm:space-y-16 sm:py-14">
        {profile.summary_cards.length > 0 ? (
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {profile.summary_cards.map((card) => (
              <div
                key={card.label}
                className="rounded-[var(--radius-lg)] border border-border bg-card p-5 shadow-sm"
              >
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
                  {card.label}
                </p>
                <p className="mt-2 text-sm font-medium leading-relaxed text-foreground">
                  {card.value}
                </p>
              </div>
            ))}
          </section>
        ) : null}

        <section className="space-y-4">
          <SectionHeader eyebrow="About" title="Partnership profile" />
          <div className="max-w-3xl space-y-4 text-sm leading-relaxed text-muted-foreground">
            {profile.partnership_blurb ? (
              <p className="text-base font-medium text-foreground">
                {profile.partnership_blurb}
              </p>
            ) : null}
            {profile.description ? <p>{profile.description}</p> : null}
            {profile.campaign_goals.length > 0 ? (
              <p>
                <span className="font-semibold text-foreground">Looking for: </span>
                {profile.campaign_goals
                  .map((g) => g.replace(/_/g, " "))
                  .join(", ")}
                .
              </p>
            ) : null}
            {profile.categories.length > 0 ? (
              <p>
                <span className="font-semibold text-foreground">Ideal events: </span>
                {profile.categories.map((c) => c.replace(/_/g, " ")).join(", ")}.
              </p>
            ) : null}
          </div>
        </section>

        <section className="space-y-5">
          <SectionHeader
            eyebrow="Activations"
            title="What they sponsor"
            description="Categories and cities this sponsor typically supports on Pàdéyá."
          />
          <div className="grid gap-8 rounded-[var(--radius-lg)] border border-border bg-muted/20 p-6 sm:grid-cols-2">
            <ChipRow items={profile.categories} label="Categories" />
            <ChipRow items={profile.target_locations} label="Locations" />
          </div>
          {profile.categories.length === 0 && profile.target_locations.length === 0 ? (
            <SectionEmpty
              title="Partnership focus coming soon"
              body="This sponsor is open to inquiries while they finalize public targeting details."
            />
          ) : null}
        </section>

        <section className="space-y-5">
          <SectionHeader
            eyebrow="Case studies"
            title="Public campaigns & case studies"
            description="Approved public case studies only — never draft, private, or internal campaigns."
          />
          {profile.public_campaigns.length === 0 ? (
            <SectionEmpty
              title="No public campaigns yet"
              body={
                profile.accepting_inquiries
                  ? "This sponsor is currently open to inquiries."
                  : "Public case studies will appear here after moderation approval."
              }
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {profile.public_campaigns.map((c) => (
                <SponsorPublicCampaignCardView key={c.id} campaign={c} />
              ))}
            </div>
          )}
        </section>

        <section id="sponsored-events-placements" className="scroll-mt-24 space-y-5">
          <SectionHeader
            eyebrow="Placements"
            title="Sponsored events & placements"
            description="Listed events with active or completed public placements — no payment or attendee data."
          />
          {profile.sponsored_events.length === 0 ? (
            <SectionEmpty
              title="No public sponsored events yet"
              body="Completed and active placements on listed events appear here — never private attendee or payment data."
            />
          ) : (
            <div className="grid gap-4">
              {profile.sponsored_events.map((ev, idx) => (
                <SponsorPublicSponsoredEventCard
                  key={`${ev.event_id ?? ev.host_id}-${idx}`}
                  event={ev}
                />
              ))}
            </div>
          )}
        </section>

        <section className="space-y-5">
          <SectionHeader
            eyebrow="Network"
            title="Hosts they have partnered with"
            description="Verified hosts with public active or completed placements."
          />
          {profile.partnered_hosts.length === 0 ? (
            <SectionEmpty
              title="No partnered hosts yet"
              body="Hosts with active or completed public placements will show here."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {profile.partnered_hosts.map((h) => (
                <SponsorPublicPartnerHostCard key={h.host_id} host={h} />
              ))}
            </div>
          )}
        </section>

        <section
          id="host-inquiry"
          className="scroll-mt-24 rounded-[var(--radius-lg)] border border-border bg-gradient-to-br from-muted/50 to-card p-8 shadow-sm"
        >
          <SectionHeader
            eyebrow="For hosts"
            title="Want this sponsor for your event?"
            description={
              profile.accepting_inquiries
                ? `${profile.display_name} is accepting partnership inquiries on Pàdéyá.`
                : `Learn how ${profile.display_name} typically partners before you reach out.`
            }
          />
          <p className="mt-4 max-w-2xl text-sm text-muted-foreground">
            {profile.summary_cards.find((c) => c.label === "Partnership style")?.value ??
              profile.partnership_blurb ??
              "Share your event package on the marketplace so brands can inquire with context."}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            {user && hasHostWorkspace ? (
              <>
                <Link href={inquiryHref}>
                  <Button>Send sponsorship inquiry</Button>
                </Link>
                <Link href={marketplaceHref}>
                  <Button variant="secondary">View matching opportunities</Button>
                </Link>
                <Link href="/host/sponsorships">
                  <Button variant="ghost">Manage your slots</Button>
                </Link>
              </>
            ) : user ? (
              <>
                <Link href={inquiryHref}>
                  <Button>Browse opportunities to inquire</Button>
                </Link>
                <Link href="/host/onboarding">
                  <Button variant="secondary">Create host profile</Button>
                </Link>
              </>
            ) : (
              <>
                <Link href={`/login?next=/sponsors/${encodeURIComponent(profile.slug)}`}>
                  <Button>Log in to pitch this sponsor</Button>
                </Link>
                <Link href="/host/onboarding">
                  <Button variant="secondary">Create host profile</Button>
                </Link>
              </>
            )}
          </div>
        </section>

        {profile.related_sponsors.length > 0 ? (
          <section className="space-y-5">
            <SectionHeader eyebrow="Discover" title="Related sponsors" />
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {profile.related_sponsors.map((s) => (
                <SponsorPublicRelatedSponsorCard key={s.slug} sponsor={s} />
              ))}
            </div>
          </section>
        ) : null}
      </Container>
    </main>
  );
}
