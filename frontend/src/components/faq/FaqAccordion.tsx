import { FaqAnswer } from "@/components/faq/FaqAnswer";
import type { FaqItem } from "@/lib/faq/faq-content";

export function FaqAccordion({ items }: { items: readonly FaqItem[] }) {
  return (
    <div className="divide-y divide-border/80 overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card/80 dark:bg-surface-elevated">
      {items.map((item) => (
        <details
          key={item.id}
          className="group px-5 py-5 transition-colors open:bg-surface-muted/50 sm:px-8 sm:py-7 dark:open:bg-paper/[0.03]"
        >
          <summary className="cursor-pointer list-none text-base font-semibold text-heading marker:content-none sm:text-lg [&::-webkit-details-marker]:hidden">
            <span className="flex items-start justify-between gap-4">
              <span className="text-balance pr-2">{item.q}</span>
              <span
                aria-hidden
                className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border text-lg leading-none text-muted-foreground transition group-open:rotate-45 group-open:border-primary/40 group-open:text-primary-text"
              >
                +
              </span>
            </span>
          </summary>
          <FaqAnswer text={item.a} />
        </details>
      ))}
    </div>
  );
}
