import Link from "next/link";

import { Button } from "@/components/ui";

/** Escalation CTAs at the bottom of the FAQ page. */
export function FaqStillNeedHelp() {
  return (
    <section className="rounded-[var(--radius-xl)] border border-border bg-card/70 px-6 py-8 dark:bg-surface-elevated/90 sm:px-8 sm:py-10">
      <h2 className="font-display text-xl font-extrabold tracking-tight text-heading sm:text-2xl">
        Still need help?
      </h2>
      <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
        If these answers didn&apos;t cover it, contact Support, open a tracked
        ticket, or browse the Help Center.
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link href="/support">
          <Button variant="secondary">Contact support</Button>
        </Link>
        <Link href="/support/new">
          <Button>Open support ticket</Button>
        </Link>
        <Link href="/help">
          <Button variant="ghost">Visit Help Center</Button>
        </Link>
      </div>
    </section>
  );
}
