/** Sort taxonomy items so those with the most available events come first. */
export function sortByEventCount<T extends { slug: string; name?: string }>(
  items: readonly T[],
  counts: Map<string, number>,
): T[] {
  return [...items].sort((a, b) => {
    const ca = counts.get(a.slug) ?? 0;
    const cb = counts.get(b.slug) ?? 0;
    if (cb !== ca) return cb - ca;
    return (a.name || a.slug).localeCompare(b.name || b.slug);
  });
}
