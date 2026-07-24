"use client";

import { useEffect } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { FanPassportCTA } from "@/components/passport/FanPassportCTA";
import { FanPassportHero } from "@/components/passport/FanPassportHero";
import { FanPassportStats } from "@/components/passport/FanPassportStats";
import { FollowedHostCards } from "@/components/passport/FollowedHostCards";
import { MerchProofSection } from "@/components/passport/MerchProofSection";
import { PassportHighlights } from "@/components/passport/PassportHighlights";
import { PassportStampGrid } from "@/components/passport/PassportStampGrid";
import { VerifiedNightsOut } from "@/components/passport/VerifiedNightsOut";
import { VerifiedReviewCards } from "@/components/passport/VerifiedReviewCards";
import { Container } from "@/components/ui";
import { trackFanPassportView } from "@/lib/analytics";
import { fanPageCtaMode, fanPageCtas, isOwnFanPassport } from "@/lib/own-fan-ctas";
import type { FanPassportPublicPage } from "@/lib/types/passport";

export function FanPassportPublicClient({
  initial,
}: {
  initial: FanPassportPublicPage;
}) {
  const page = initial;
  const { user, loading: authLoading } = useAuth();

  useEffect(() => {
    if (page.username) trackFanPassportView({ username: page.username });
  }, [page.username]);

  // Prefer user id: isOwnPassport = current_user?.id === passport_owner_user_id
  const isOwnPassport = isOwnFanPassport(user?.id, page.user_id);
  const ownershipReady = !authLoading;
  const fanCtas = fanPageCtas(fanPageCtaMode(isOwnPassport));

  return (
    <main className="min-w-0 overflow-x-clip bg-background">
      <FanPassportHero
        page={page}
        isOwnPassport={isOwnPassport}
        ownershipReady={ownershipReady}
        ctas={fanCtas}
      />

      <Container className="max-w-[1180px] space-y-14 py-10 sm:space-y-16 sm:py-14">
        <FanPassportStats page={page} />

        <PassportStampGrid badges={page.badges} />

        <MerchProofSection
          badges={page.badges}
          summaries={page.merch_proof_summaries}
        />

        <VerifiedNightsOut events={page.attended_events} />
        <FollowedHostCards hosts={page.followed_hosts} />
        <VerifiedReviewCards reviews={page.reviews} />
        <PassportHighlights page={page} />

        {page.vault_unlocks.length > 0 ? (
          <section className="space-y-4">
            <div>
              <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-muted-foreground">
                Vault
              </p>
              <h2 className="mt-1 text-xl font-extrabold tracking-tight text-foreground sm:text-2xl">
                Unlocked drops
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Titles only — locked Vault content is never shown here.
              </p>
            </div>
            <ul className="grid gap-3 sm:grid-cols-2">
              {page.vault_unlocks.map((v) => (
                <li
                  key={`${v.title}-${v.host_username}`}
                  className="rounded-[var(--radius-lg)] border border-border bg-card px-4 py-4"
                >
                  <p className="font-extrabold text-foreground">{v.title}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {v.access_label}
                    {v.host_username ? ` · @${v.host_username}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <FanPassportCTA
          isOwnPassport={isOwnPassport}
          displayName={page.display_name}
          sharePath={page.share_path}
          ctas={fanCtas}
        />
      </Container>
    </main>
  );
}
