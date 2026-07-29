"use client";

import Link from "next/link";
import { type ReactNode } from "react";

import { CreateEventCta } from "@/components/layout/CreateEventCta";
import { headerDarkSurfaceProps } from "@/components/layout/headerSurface";
import { Button, Container, Logo } from "@/components/ui";
import { brand } from "@/lib/brand";
import { cn } from "@/lib/cn";

const LOGIN_HERO_BULLETS = [
  {
    title: "Tickets you can trust",
    body: "QR codes only after payment is confirmed, with no guesswork at the door.",
  },
  {
    title: "Fan life in one place",
    body: "Passport, merch orders, Vault unlocks, and messages under your username.",
  },
  {
    title: "Host with proof",
    body: "Events, check-in, merch, promos, and payouts with a Legacy Page fans trust.",
  },
] as const;

const FORM_CARD_CLASS = cn(
  "w-full space-y-6 rounded-[var(--radius-xl)] border border-paper/12",
  "bg-paper/[0.06] p-6 shadow-[0_20px_60px_rgb(0_0_0/0.45)] backdrop-blur-xl sm:p-8",
  "ring-1 ring-paper/5",
);

type Props = {
  title: string;
  description: string;
  children: ReactNode;
  footer?: ReactNode;
};

export function LoginPageLayout({
  title,
  description,
  children,
  footer,
}: Props) {
  return (
    <div
      {...headerDarkSurfaceProps}
      className="flex min-h-[calc(100vh-4rem)] flex-col bg-ink text-paper"
    >
      <main
        {...headerDarkSurfaceProps}
        className="relative flex flex-1 flex-col overflow-x-hidden"
      >
        <div
          aria-hidden
          className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-90"
        />
        <div
          aria-hidden
          className="padeya-grain pointer-events-none absolute inset-0 opacity-35"
        />

        <Container className="relative flex-1 px-4 py-12 sm:px-6 sm:py-14 lg:px-8 lg:py-16 xl:py-20">
          <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-12 xl:gap-16">
            <div className="min-w-0 w-full max-w-[560px] justify-self-center lg:justify-self-end lg:pr-2 xl:pr-4">
              <div className="space-y-7 sm:space-y-8">
                <div className="hidden lg:block">
                  <Logo variant="dark" height={44} href={undefined} />
                </div>
                <div className="mb-6 flex justify-center lg:hidden">
                  <Logo variant="dark" height={40} href={undefined} />
                </div>
                <div className="space-y-4 sm:space-y-5">
                  <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#8EF012]">
                    Fans & hosts · {brand.name}
                  </p>
                  <h2 className="text-balance font-display text-2xl font-extrabold tracking-tight sm:text-3xl lg:text-[2.35rem] lg:leading-[1.12]">
                    {brand.tagline}
                  </h2>
                  <p className="max-w-[32rem] text-sm leading-relaxed text-paper/80 sm:text-base lg:text-[1.05rem]">
                    Sign in or create an account to manage tickets, build your Fan
                    Passport, unlock Vault drops, and run events with reputation
                    that travels with you.
                  </p>
                </div>
                <ul className="max-w-[32rem] space-y-4 border-t border-paper/10 pt-6">
                  {LOGIN_HERO_BULLETS.map((item) => (
                    <li key={item.title} className="space-y-1">
                      <p className="text-sm font-bold text-paper">{item.title}</p>
                      <p className="text-sm leading-relaxed text-paper/70">
                        {item.body}
                      </p>
                    </li>
                  ))}
                </ul>
                <p className="text-sm text-paper/65">
                  Not ready to sign up?{" "}
                  <Link
                    href="/events"
                    className="font-semibold text-[#8EF012] hover:underline"
                  >
                    Browse events
                  </Link>
                  {" · "}
                  <Link
                    href="/merch"
                    className="font-semibold text-paper underline-offset-2 hover:text-[#8EF012] hover:underline"
                  >
                    Shop merch
                  </Link>
                </p>
              </div>
            </div>

            <div className="min-w-0 w-full max-w-[540px] justify-self-center lg:justify-self-start lg:pl-2 xl:pl-4">
              <div className={FORM_CARD_CLASS}>
                <div className="space-y-2">
                  <h1 className="text-2xl font-extrabold tracking-tight text-paper sm:text-[1.65rem]">
                    {title}
                  </h1>
                  <p className="text-sm leading-relaxed text-paper/70 sm:text-base">
                    {description}
                  </p>
                </div>
                {children}
                {footer}
              </div>
            </div>
          </div>
        </Container>

        <div
          aria-hidden
          className="pointer-events-none h-px w-full bg-gradient-to-r from-transparent via-paper/10 to-transparent"
        />
        <div className="relative bg-gradient-to-b from-transparent via-paper/[0.02] to-paper/[0.04]">
          <Container className="px-4 py-10 sm:px-6 sm:py-12 lg:px-8 lg:py-14">
            <section
              aria-label="Explore Pàdéyá"
              className="rounded-[var(--radius-xl)] border border-paper/10 bg-paper/[0.04] px-5 py-6 sm:px-8 sm:py-8"
            >
              <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 max-w-xl space-y-2">
                  <h2 className="font-display text-xl font-extrabold tracking-tight text-paper sm:text-2xl">
                    Ready for your next adventure?
                  </h2>
                  <p className="text-sm leading-relaxed text-paper/70 sm:text-base">
                    Discover events, shop merch, or create an event on {brand.name}.
                  </p>
                </div>
                <div className="flex w-full min-w-0 flex-col gap-2.5 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center sm:justify-end">
                  <Link href="/events" className="w-full sm:w-auto">
                    <Button
                      variant="outline-dark"
                      size="lg"
                      className="w-full sm:min-w-[9.5rem]"
                    >
                      Explore events
                    </Button>
                  </Link>
                  <Link href="/merch" className="w-full sm:w-auto">
                    <Button
                      variant="outline-dark"
                      size="lg"
                      className="w-full sm:min-w-[9.5rem]"
                    >
                      Shop merch
                    </Button>
                  </Link>
                  <CreateEventCta
                    className="w-full sm:w-auto"
                    buttonVariant="primary-on-dark"
                    buttonSize="lg"
                  />
                </div>
              </div>
            </section>
          </Container>
        </div>
      </main>
    </div>
  );
}
