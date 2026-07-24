import { Container, SectionHeader } from "@/components/ui";

const FAN_STEPS = [
  { title: "Discover events", body: "Browse by city, category, and vibe." },
  { title: "Buy secure tickets", body: "Checkout that protects both sides." },
  { title: "Check in with QR", body: "Verified entry at the door." },
  { title: "Leave verified reviews", body: "Ratings only after check-in." },
] as const;

const HOST_STEPS = [
  { title: "Create event", body: "Pages, tiers, privacy, and policies." },
  { title: "Sell tickets", body: "Tables, VIP, promos, and capacity." },
  { title: "Scan guests", body: "Staff QR check-in when it matters." },
  { title: "Build your Legacy Page", body: "Reputation that outlasts the night." },
] as const;

function Track({
  eyebrow,
  title,
  steps,
}: {
  eyebrow: string;
  title: string;
  steps: readonly { title: string; body: string }[];
}) {
  return (
    <div className="flex h-full flex-col space-y-6 rounded-[var(--radius-xl)] border border-border bg-card p-6 shadow-[var(--shadow-soft)] sm:p-8 dark:bg-surface-elevated dark:shadow-[var(--shadow)]">
      <div className="space-y-1.5">
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
          {eyebrow}
        </p>
        <h3 className="text-xl font-extrabold tracking-tight text-foreground sm:text-2xl">
          {title}
        </h3>
      </div>
      <ol className="flex flex-1 flex-col space-y-5">
        {steps.map((step, index) => (
          <li key={step.title} className="flex gap-4">
            <span
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-sm font-extrabold text-accent"
              aria-hidden
            >
              {index + 1}
            </span>
            <div className="min-w-0 space-y-1 pt-0.5">
              <p className="text-base font-bold text-foreground">{step.title}</p>
              <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
                {step.body}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function HomeHowItWorks() {
  return (
    <section className="bg-muted py-16 sm:py-20">
      <Container className="space-y-10">
        <SectionHeader
          eyebrow="How it works"
          title="One marketplace. Two clear journeys."
          description="Fans get trusted nights out. Hosts get the ops stack to sell, scan, and grow."
        />
        <div className="grid auto-rows-fr gap-6 lg:grid-cols-2">
          <Track
            eyebrow="For fans"
            title="From discovery to verified review"
            steps={FAN_STEPS}
          />
          <Track
            eyebrow="For hosts"
            title="From create to Legacy"
            steps={HOST_STEPS}
          />
        </div>
      </Container>
    </section>
  );
}
