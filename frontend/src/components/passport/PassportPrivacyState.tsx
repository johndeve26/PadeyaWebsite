"use client";

import Link from "next/link";

import { Button, Container } from "@/components/ui";

type Props = {
  variant?: "private" | "unavailable";
};

export function PassportPrivacyState({ variant = "private" }: Props) {
  const title =
    variant === "private"
      ? "This Fan Passport is private."
      : "Fan Passport unavailable.";
  const text =
    variant === "private"
      ? "The owner controls what appears publicly on Pàdéyá. If this is your Passport, set visibility to Public or Unlisted in Passport settings, then save."
      : "This Passport may be private, unlisted, or no longer available.";

  return (
    <main className="bg-background py-16 sm:py-20">
      <Container className="max-w-xl">
        <div className="rounded-[var(--radius-xl)] border border-border bg-card px-6 py-10 text-center shadow-[var(--shadow-soft)]">
          <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-muted-foreground">
            Fan Passport
          </p>
          <h1 className="mt-3 text-2xl font-extrabold tracking-tight text-foreground">
            {title}
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
            {text}
          </p>
          <div className="mt-6 flex flex-col items-center gap-2 sm:flex-row sm:justify-center">
            <Link href="/dashboard/passport/settings">
              <Button>Passport settings</Button>
            </Link>
            <Link href="/events">
              <Button variant="secondary">Discover events</Button>
            </Link>
            <Link href="/fans">
              <Button variant="secondary">Fan Directory</Button>
            </Link>
          </div>
        </div>
      </Container>
    </main>
  );
}
