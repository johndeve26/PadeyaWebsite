import Link from "next/link";

import { Button } from "@/components/ui";

/** Escalation CTAs after Help — ticket, contact, report, appeal. */
export function HelpStillNeedHelp() {
  return (
    <section className="border-t border-border pt-10">
      <h2 className="font-display text-xl font-extrabold tracking-tight text-heading">
        Still need help?
      </h2>
      <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
        If this guide didn&apos;t solve it, open a tracked ticket or use the
        safety and appeals paths below.
      </p>
      <div className="mt-5 flex flex-wrap gap-3">
        <Link href="/support">
          <Button>Open support ticket</Button>
        </Link>
        <Link href="/support">
          <Button variant="secondary">Contact support</Button>
        </Link>
        <Link href="/report">
          <Button variant="ghost">Report an issue</Button>
        </Link>
        <Link href="/help/articles/how-to-appeal-restriction">
          <Button variant="ghost">Appeal account restriction</Button>
        </Link>
      </div>
    </section>
  );
}
