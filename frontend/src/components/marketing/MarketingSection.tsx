import type { ReactNode } from "react";

import { Container, SectionHeader } from "@/components/ui";
import { cn } from "@/lib/cn";

type MarketingSectionProps = {
  id?: string;
  eyebrow?: string;
  title: string;
  description?: string;
  tone?: "light" | "dark" | "muted" | "ink-soft";
  children: ReactNode;
  className?: string;
  /** Soft entrance for the first content band after hero. */
  animate?: boolean;
  headerAction?: ReactNode;
};

export function MarketingSection({
  id,
  eyebrow,
  title,
  description,
  tone = "light",
  children,
  className = "",
  animate = false,
  headerAction,
}: MarketingSectionProps) {
  const tones = {
    light: "bg-background text-foreground",
    muted: "bg-surface-muted text-foreground",
    dark: "relative overflow-hidden bg-ink text-paper",
    "ink-soft":
      "relative overflow-hidden bg-[linear-gradient(165deg,var(--ink)_0%,color-mix(in_srgb,var(--ink)_92%,var(--primary)_8%)_48%,var(--surface-dark)_100%)] text-paper",
  } as const;

  const headerTone = tone === "light" || tone === "muted" ? "light" : "dark";

  return (
    <section
      id={id}
      className={cn(tones[tone], "py-16 sm:py-20 md:py-24", className)}
    >
      {tone === "dark" || tone === "ink-soft" ? (
        <>
          <div
            aria-hidden
            className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-80"
          />
          <div
            aria-hidden
            className="padeya-grain pointer-events-none absolute inset-0 opacity-40"
          />
        </>
      ) : null}
      <Container className={cn("relative space-y-10 sm:space-y-14", animate && "padeya-fade-up")}>
        <SectionHeader
          variant="display"
          tone={headerTone}
          eyebrow={eyebrow}
          title={title}
          description={description}
          action={headerAction}
        />
        {children}
      </Container>
    </section>
  );
}
