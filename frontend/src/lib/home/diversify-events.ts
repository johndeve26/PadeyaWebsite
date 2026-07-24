import type { EventItem } from "@/lib/types/events";

const HOMEPAGE_EVENT_LIMIT = 8;

/** Prefer a mix of categories so the homepage grid doesn’t look identical. */
export function diversifyHomepageEvents(
  rows: EventItem[],
  limit = HOMEPAGE_EVENT_LIMIT,
): EventItem[] {
  const featured = rows.filter((e) => e.featured);
  const pool = featured.length ? [...featured, ...rows] : [...rows];
  const seen = new Set<string>();
  const byCategory = new Map<string, EventItem[]>();
  for (const event of pool) {
    if (seen.has(event.id)) continue;
    seen.add(event.id);
    const key = event.category?.slug || event.category_id || "other";
    const list = byCategory.get(key) ?? [];
    list.push(event);
    byCategory.set(key, list);
  }
  const picked: EventItem[] = [];
  const keys = Array.from(byCategory.keys());
  let guard = 0;
  while (picked.length < limit && guard < limit * keys.length + 4) {
    for (const key of keys) {
      const list = byCategory.get(key);
      if (!list?.length) continue;
      const next = list.shift();
      if (next) picked.push(next);
      if (picked.length >= limit) break;
    }
    guard += 1;
  }
  return picked;
}

export { HOMEPAGE_EVENT_LIMIT };
