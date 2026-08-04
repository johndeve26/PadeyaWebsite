import type { Metadata } from "next";
import Link from "next/link";

import { Button, Container } from "@/components/ui";

export const metadata: Metadata = {
  title: "How Legacy works | Pàdéyá",
  description:
    "Legacy Score and Legacy Tier measure verified hosting history on Pàdéyá — not a star rating and not a guarantee of future events.",
};

const WEIGHTS = [
  { label: "Verified rating", weight: "30%", detail: "Average verified rating ÷ 5 × 100. Uses 0 when there are no verified reviews." },
  { label: "Completed events", weight: "15%", detail: "Completed event count ÷ 20 × 100, capped at 100." },
  { label: "Tickets sold", weight: "15%", detail: "Verified tickets sold ÷ 5,000 × 100, capped at 100." },
  { label: "Verified check-ins", weight: "15%", detail: "Verified check-in count ÷ 3,000 × 100, capped at 100." },
  { label: "Refund / dispute record", weight: "10%", detail: "100 − verified refund/dispute rate. Uses a default of 80 when the rate is unknown." },
  { label: "Consistency", weight: "10%", detail: "50% verified check-in rate + 50% event completion rate." },
  { label: "Followers and repeat buyers", weight: "5%", detail: "50% follower progress toward 2,000 + 50% repeat-buyer percentage." },
] as const;

export default function LegacyHowItWorksPage() {
  return (
    <main className="min-w-0">
      <section className="border-b border-border bg-surface">
        <Container className="py-12 sm:py-16">
          <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-muted-foreground">
            Pàdéyá Legacy
          </p>
          <h1 className="mt-3 max-w-2xl text-4xl font-extrabold tracking-tight text-heading">
            How Legacy works
          </h1>
          <p className="mt-4 max-w-2xl text-body">
            Legacy Score is a 0–100 composite from verified host activity. Legacy Tier
            also requires hard activity gates. It is not a five-star rating, not a
            public ranking, and not a guarantee of future event quality or safety.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/hosts">
              <Button size="lg">Explore hosts</Button>
            </Link>
            <Link href="/host/legacy/tier">
              <Button size="lg" variant="secondary">
                Host tier progress
              </Button>
            </Link>
          </div>
        </Container>
      </section>

      <Container className="space-y-12 py-12 sm:py-16">
        <section className="max-w-3xl space-y-3">
          <h2 className="text-2xl font-extrabold text-heading">Score versus tier</h2>
          <p className="text-body">
            <strong className="text-heading">Legacy Score</strong> is the weighted
            composite. Public profiles show it as a whole number out of 100.
          </p>
          <p className="text-body">
            <strong className="text-heading">Legacy Tier</strong> is the highest
            configured tier where the score meets the minimum and every hard gate
            passes — completed events, tickets sold, verified check-ins, verified
            reviews, and average verified rating where required.
          </p>
          <p className="text-body">
            A host can sit in a score range associated with a higher tier while still
            remaining on a lower tier until the remaining activity gates are met.
          </p>
        </section>

        <section className="max-w-3xl space-y-4">
          <h2 className="text-2xl font-extrabold text-heading">What shapes the score</h2>
          <ul className="space-y-3">
            {WEIGHTS.map((row) => (
              <li
                key={row.label}
                className="rounded-[var(--radius-md)] border border-border bg-card px-4 py-3 dark:bg-surface-elevated"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-bold text-heading">{row.label}</p>
                  <p className="text-sm font-extrabold text-primary">{row.weight}</p>
                </div>
                <p className="mt-1 text-sm text-body">{row.detail}</p>
              </li>
            ))}
          </ul>
          <p className="text-sm text-muted-foreground">
            Activity above a factor’s normalization cap still has broader product
            value; only that specific factor is capped for scoring.
          </p>
        </section>

        <section className="max-w-3xl space-y-3">
          <h2 className="text-2xl font-extrabold text-heading">Verified evidence</h2>
          <p className="text-body">
            Public Legacy summaries highlight verified rating, verified reviews,
            completed events, tickets sold, verified check-ins, and repeat buyers when
            available. Owner self-actions are excluded from relevant Legacy inputs.
          </p>
        </section>

        <section className="max-w-3xl space-y-3">
          <h2 className="text-2xl font-extrabold text-heading">Provisional status</h2>
          <p className="text-body">
            Hosts with limited verified history — currently fewer than 3 completed
            events or fewer than 5 verified reviews — may show as Provisional. That
            label does not reduce the calculated score or change the tier formula. It
            signals that the standing may move more quickly as more verified activity
            is recorded.
          </p>
        </section>

        <section className="max-w-3xl space-y-3">
          <h2 className="text-2xl font-extrabold text-heading">When scores update</h2>
          <p className="text-body">
            Legacy Score is stored and recalculated after important verified activity,
            such as event completion, verified reviews, tier progress views, or an
            authorized recalculation. Public profile views use the latest stored score
            and do not recalculate on every open. Follower counts may update visibly
            before the follower contribution inside the composite is fully recalculated.
          </p>
        </section>

        <section className="max-w-3xl space-y-3 rounded-[var(--radius-lg)] border border-border bg-surface-muted px-5 py-4">
          <h2 className="text-lg font-extrabold text-heading">Important</h2>
          <p className="text-sm text-body">
            Legacy reflects verified historical activity on Pàdéyá. It is not a
            guarantee of future event quality, safety, availability or financial
            performance.
          </p>
        </section>
      </Container>
    </main>
  );
}
