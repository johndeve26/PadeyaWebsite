import Link from "next/link";

import { HELP_ROLE_CARDS } from "@/lib/help-quick-links";

export function HelpRoleCards() {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {HELP_ROLE_CARDS.map((card) => (
        <li key={card.title}>
          <Link
            href={card.href}
            className="group block border-b border-border py-5 transition-colors hover:border-primary"
          >
            <p className="font-display text-lg font-extrabold tracking-tight text-heading transition-colors group-hover:text-primary-text">
              {card.title}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">{card.description}</p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
