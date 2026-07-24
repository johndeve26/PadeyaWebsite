import Link from "next/link";

import type { HelpCategory } from "@/lib/knowledge-base/api";
import { HELP_GROUP_LABELS } from "@/lib/knowledge-base/api";

const GROUP_ORDER = [
  "fan",
  "host",
  "sponsor",
  "ambassador",
  "account",
  "payments",
  "admin",
  "general",
];

export function HelpCategoryGrid({ categories }: { categories: HelpCategory[] }) {
  const byGroup = new Map<string, HelpCategory[]>();
  for (const cat of categories) {
    const key = cat.group_key || "general";
    const list = byGroup.get(key) || [];
    list.push(cat);
    byGroup.set(key, list);
  }

  const groups = GROUP_ORDER.filter((g) => byGroup.has(g)).concat(
    [...byGroup.keys()].filter((g) => !GROUP_ORDER.includes(g)),
  );

  return (
    <div className="space-y-12">
      {groups.map((group) => {
        const items = byGroup.get(group) || [];
        return (
          <section key={group}>
            <h2 className="font-display text-xl font-extrabold tracking-tight text-heading sm:text-2xl">
              {HELP_GROUP_LABELS[group] || group}
            </h2>
            <ul className="mt-5 grid gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((cat) => (
                <li key={cat.id}>
                  <Link
                    href={`/help/${cat.slug}`}
                    className="group flex items-baseline justify-between gap-3 border-b border-border py-3 transition-colors hover:border-primary"
                  >
                    <span className="font-semibold text-heading transition-colors group-hover:text-primary-text">
                      {cat.name}
                    </span>
                    <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                      {cat.article_count}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
