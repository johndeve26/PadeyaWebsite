/** Lowercase + hyphenate a display label into a URL-safe slug. */
export function slugifyLabel(s: string): string {
  return s
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** City name → discovery slug (e.g. "Lagos" → "lagos"). */
export function citySlugFromName(name: string): string {
  return slugifyLabel(name);
}

/** True when a free-text city matches a city hub slug. */
export function matchCitySlug(
  city: string | null | undefined,
  slug: string,
): boolean {
  if (!city || !slug) return false;
  return citySlugFromName(city) === slugifyLabel(slug);
}
