import Link from "next/link";
import { type ReactNode } from "react";

import { headerDarkSurfaceProps } from "@/components/layout/headerSurface";
import { Card, Container, Logo } from "@/components/ui";
import { brand } from "@/lib/brand";

export function AuthFormCard({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <main
      {...headerDarkSurfaceProps}
      className="relative min-h-[78vh] overflow-hidden bg-ink py-12 sm:py-16"
    >
      <div aria-hidden className="padeya-hero-glow pointer-events-none absolute inset-0" />
      <div aria-hidden className="padeya-grain pointer-events-none absolute inset-0 opacity-40" />
      <Container className="relative grid gap-10 lg:grid-cols-[1fr_420px] lg:items-center">
        <div className="hidden space-y-6 text-paper lg:block">
          <Logo variant="dark" height={44} />
          <p className="max-w-md text-3xl font-extrabold tracking-tight sm:text-4xl">
            {brand.tagline}
          </p>
          <p className="max-w-md text-base leading-relaxed text-paper/75">
            Secure tickets, verified host reputation, Vault exclusives, and Fan
            Passport — all in one Pàdéyá account.
          </p>
          <ul className="space-y-3 text-sm text-paper/75">
            {[
              "Payment-confirmed tickets before QR issues",
              "Legacy Pages with verified attendee reviews",
              "Host tools for check-in, promos, and payouts",
            ].map((item) => (
              <li key={item} className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                {item}
              </li>
            ))}
          </ul>
          <p className="text-sm text-paper/70">
            New here?{" "}
            <Link href="/events" className="font-semibold text-primary hover:underline">
              Browse events
            </Link>
          </p>
        </div>

        <div className="space-y-6">
          <div className="flex justify-center lg:hidden">
            <Logo variant="dark" height={40} />
          </div>
          <Card className="space-y-6 shadow-[var(--shadow-strong)] dark:border-border-strong/40">
            <div className="space-y-2.5">
              <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
                {title}
              </h1>
              <p className="text-base leading-relaxed text-muted-foreground">
                {description}
              </p>
            </div>
            {children}
            {footer}
          </Card>
        </div>
      </Container>
    </main>
  );
}
