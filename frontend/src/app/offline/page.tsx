import type { Metadata } from "next";
import Link from "next/link";

import { Button, Card, Container, Logo } from "@/components/ui";

export const metadata: Metadata = {
  title: "Offline",
  description: "You’re offline — cached Pàdéyá tickets may still open.",
  robots: { index: false, follow: false },
};

export default function OfflinePage() {
  return (
    <main className="relative flex min-h-[75vh] items-center overflow-hidden bg-background py-16 text-foreground">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_0%,color-mix(in_srgb,var(--primary)_14%,transparent),transparent_60%)]"
      />
      <Container width="narrow" className="relative">
        <Card className="space-y-8 border-border p-6 text-center shadow-[var(--shadow)] sm:p-10 dark:bg-surface-elevated">
          <div className="flex justify-center">
            <Logo variant="auto" height={40} />
          </div>
          <div className="space-y-4">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">
              Connection
            </p>
            <h1 className="text-3xl font-extrabold tracking-tight text-heading sm:text-4xl">
              You’re offline
            </h1>
            <p className="text-base leading-relaxed text-muted-foreground sm:text-lg">
              Pàdéyá can’t reach the network right now. Cached tickets may still
              open from My Tickets. Vault, checkout, and payments stay
              online-only.
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/dashboard/tickets">
              <Button size="lg">My tickets</Button>
            </Link>
            <Link href="/events">
              <Button size="lg" variant="secondary">
                Events
              </Button>
            </Link>
          </div>
        </Card>
      </Container>
    </main>
  );
}
