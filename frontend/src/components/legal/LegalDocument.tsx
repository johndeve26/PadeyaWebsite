import Link from "next/link";
import type { ReactNode } from "react";

import { PublicPageShell } from "@/components/marketing/PublicPageShell";

export type LegalTocItem = {
  id: string;
  title: string;
};

type LegalDocumentProps = {
  title: string;
  description: string;
  updatedLabel?: string;
  /** In-page table of contents (anchors must match section `id`s). */
  toc?: readonly LegalTocItem[];
  children: ReactNode;
};

/** Shared layout for public policy and guidelines pages. */
export function LegalDocument({
  title,
  description,
  updatedLabel = "Last updated: July 2026",
  toc,
  children,
}: LegalDocumentProps) {
  return (
    <PublicPageShell
      eyebrow="Policies"
      title={title}
      description={description}
      narrow
    >
      <div className="mx-auto max-w-3xl space-y-8">
        <p className="text-center text-sm text-muted-foreground">{updatedLabel}</p>
        {toc && toc.length > 0 ? <LegalToc items={toc} /> : null}
        <article className="prose prose-neutral dark:prose-invert max-w-none space-y-10 text-base leading-relaxed text-foreground prose-headings:font-display prose-headings:text-heading prose-a:text-primary">
          {children}
        </article>
        <p className="border-t border-border pt-6 text-sm text-muted-foreground">
          Questions? Visit{" "}
          <Link href="/support" className="font-semibold text-primary">
            Support
          </Link>{" "}
          or{" "}
          <Link href="/contact" className="font-semibold text-primary">
            Contact
          </Link>
          .
        </p>
      </div>
    </PublicPageShell>
  );
}

/** Sticky-friendly in-page TOC for long policy documents. */
export function LegalToc({ items }: { items: readonly LegalTocItem[] }) {
  return (
    <nav
      aria-label="On this page"
      className="rounded-[var(--radius-lg)] border border-border bg-card/70 p-5 sm:p-6 dark:bg-surface-elevated"
    >
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary">
        On this page
      </p>
      <ol className="mt-4 columns-1 gap-x-8 space-y-2 sm:columns-2">
        {items.map((item) => (
          <li key={item.id} className="break-inside-avoid">
            <a
              href={`#${item.id}`}
              className="text-sm font-semibold text-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {item.title}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

export function LegalSection({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-28 space-y-3">
      <h2 className="text-xl font-extrabold tracking-tight text-heading">{title}</h2>
      <div className="space-y-3 text-muted-foreground [&_a]:font-semibold [&_a]:text-primary [&_ul]:list-disc [&_ul]:space-y-1.5 [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:space-y-1.5 [&_ol]:pl-5">
        {children}
      </div>
    </section>
  );
}
