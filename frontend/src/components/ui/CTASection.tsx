import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Container } from "./Container";

export function CTASection({
  title,
  description,
  actions,
  tone = "light",
  className = "",
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  tone?: "light" | "dark" | "accent";
  className?: string;
}) {
  const tones = {
    light: "bg-muted text-foreground border-t border-border",
    dark: "bg-ink text-paper",
    accent:
      "bg-[linear-gradient(120deg,color-mix(in_srgb,var(--primary)_18%,transparent),var(--surface)_45%,var(--card))] text-foreground border-t border-border",
  };

  return (
    <section className={cn(tones[tone], "py-14 sm:py-16", className)}>
      <Container className="flex flex-col items-stretch justify-between gap-6 sm:flex-row sm:items-center sm:gap-8">
        <div className="max-w-2xl space-y-2.5">
          <h2 className="text-balance text-2xl font-extrabold tracking-tight sm:text-3xl">
            {title}
          </h2>
          {description ? (
            <p
              className={cn(
                "text-base leading-relaxed sm:text-lg",
                tone === "dark" ? "text-paper/75" : "text-muted-foreground",
              )}
            >
              {description}
            </p>
          ) : null}
        </div>
        {actions ? (
          <div className="flex w-full shrink-0 flex-col gap-3 sm:w-auto sm:flex-row sm:flex-wrap">
            {actions}
          </div>
        ) : null}
      </Container>
    </section>
  );
}
