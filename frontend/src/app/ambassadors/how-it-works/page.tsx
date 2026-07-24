import Link from "next/link";

import { Button, Container } from "@/components/ui";

const steps = [
  {
    title: "Create a Pàdéyá account",
    body: "You need an active account. Ambassadors is open — not invite-only.",
  },
  {
    title: "Pick an eligible event",
    body: "Browse events with open Ambassadors enabled and tap Promote this event.",
  },
  {
    title: "Accept Ambassador terms",
    body: "Confirm you understand this is a promoter role only — not host team or scanner access.",
  },
  {
    title: "Share your link or code",
    body: "You instantly get a unique Ambassador link (?ref=) and Ambassador code to share.",
  },
  {
    title: "Track performance",
    body: "See clicks, confirmed ticket sales, merch sales when enabled, and estimated earnings.",
  },
  {
    title: "Earnings & payouts",
    body: "Estimated earnings update from verified paid orders. Approved and payable balances appear when payouts are processed.",
  },
];

export default function AmbassadorsHowItWorksPage() {
  return (
    <main className="min-w-0">
      <section className="border-b border-border bg-surface">
        <Container className="py-12 sm:py-16">
          <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-muted-foreground">
            Pàdéyá Ambassadors
          </p>
          <h1 className="mt-3 max-w-2xl text-4xl font-extrabold tracking-tight text-heading">
            How Ambassadors works
          </h1>
          <p className="mt-4 max-w-xl text-body">
            Ambassadors promote events. Host teams run operations. They stay completely
            separate — becoming an ambassador never grants dashboard, scanner, or staff
            permissions.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/ambassadors/events">
              <Button size="lg">Find events to promote</Button>
            </Link>
            <Link href="/dashboard/ambassador">
              <Button size="lg" variant="secondary">
                Go to dashboard
              </Button>
            </Link>
          </div>
        </Container>
      </section>

      <Container className="space-y-8 py-12 sm:py-16">
        <ol className="space-y-6">
          {steps.map((step, index) => (
            <li key={step.title} className="flex gap-4">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-sm font-extrabold text-paper">
                {index + 1}
              </span>
              <div>
                <h2 className="text-lg font-extrabold text-heading">{step.title}</h2>
                <p className="mt-1 text-sm text-body">{step.body}</p>
              </div>
            </li>
          ))}
        </ol>

        <div className="border border-border bg-card p-5 sm:p-6">
          <h2 className="text-lg font-extrabold text-heading">What you never get</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-body">
            <li>Host dashboard or host team permissions</li>
            <li>Scanner, merch pickup, or event staff access</li>
            <li>Buyer private data, attendee lists, or payment references</li>
          </ul>
        </div>
      </Container>
    </main>
  );
}
