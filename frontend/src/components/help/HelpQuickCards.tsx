import Link from "next/link";

import { HELP_QUICK_CARDS } from "@/lib/help-quick-links";

export function HelpQuickCards() {
  return (
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {HELP_QUICK_CARDS.map((card) => (
        <li key={card.title}>
          <Link
            href={card.href}
            className="group flex h-full flex-col border-b border-border py-4 transition-colors hover:border-primary"
          >
            <span className="font-semibold text-heading transition-colors group-hover:text-primary-text">
              {card.title}
            </span>
            <span className="mt-1 text-sm text-muted-foreground">
              {card.description}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
