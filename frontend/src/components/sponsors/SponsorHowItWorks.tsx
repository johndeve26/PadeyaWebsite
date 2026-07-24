import { SectionHeader } from "@/components/ui";
import { cn } from "@/lib/cn";

const DEFAULT_STEPS = [
  {
    title: "Browse verified hosts",
    body: "Shortlist creators with Legacy proof and checked-in audience history.",
    mark: "◎",
  },
  {
    title: "Pick a sponsorship slot",
    body: "Choose logo, booth, Vault, Memory, or custom packages with clear pricing.",
    mark: "◇",
  },
  {
    title: "Send an inquiry",
    body: "Share brand brief and budget. Hosts review every request.",
    mark: "→",
  },
  {
    title: "Track placement impact",
    body: "Confirmed placements can surface impressions and clicks for accountability.",
    mark: "✦",
  },
];

export function SponsorHowItWorks({
  eyebrow = "How it works",
  title = "How sponsorship works on Pàdéyá",
  description = "Four simple steps from discovery to placement.",
  steps = DEFAULT_STEPS,
  tone = "light",
  className = "",
}: {
  eyebrow?: string;
  title?: string;
  description?: string;
  steps?: { title: string; body: string; mark?: string }[];
  tone?: "light" | "dark";
  className?: string;
}) {
  const dark = tone === "dark";

  return (
    <section className={cn("space-y-5", className)}>
      <SectionHeader
        tone={tone}
        eyebrow={eyebrow}
        title={title}
        description={description}
      />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step, index) => (
          <div
            key={step.title}
            className={cn(
              "relative space-y-2 rounded-[var(--radius-lg)] border px-4 py-4",
              dark
                ? "border-paper/10 bg-paper/5"
                : "border-border bg-card dark:bg-surface-elevated",
            )}
          >
            <div className="flex items-center gap-2.5">
              <span
                className={cn(
                  "inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-extrabold",
                  dark
                    ? "bg-accent text-primary-foreground"
                    : "bg-ink text-accent",
                )}
              >
                {index + 1}
              </span>
              <span
                aria-hidden
                className={cn(
                  "text-sm",
                  dark ? "text-accent" : "text-muted-foreground",
                )}
              >
                {step.mark || "·"}
              </span>
            </div>
            <h3
              className={cn(
                "text-sm font-bold leading-snug sm:text-base",
                dark ? "text-paper" : "text-foreground",
              )}
            >
              {step.title}
            </h3>
            <p
              className={cn(
                "text-xs leading-relaxed sm:text-sm",
                dark ? "text-subtle-foreground" : "text-muted-foreground",
              )}
            >
              {step.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
