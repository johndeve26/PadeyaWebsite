/** Shared ISR / fetch revalidation TTLs for public Pàdéyá surfaces. */

export const PUBLIC_REVALIDATE = {
  /** Home, marketing, legal, FAQ (mostly static). */
  marketing: 3600,
  /** Event list shells / discovery hubs. */
  eventsList: 90,
  /** Public event detail. */
  eventDetail: 120,
  /** Host / fan directories. */
  profiles: 180,
  /** Blog / help articles (also tagged). */
  content: 300,
  /** Taxonomy / browse tiles. */
  taxonomy: 1800,
  /** Featured picks / homepage rails. */
  featured: 120,
  /** Calendar / map / nearby (capacity-sensitive-ish). */
  discoveryGeo: 90,
} as const;

export type PublicRevalidateKey = keyof typeof PUBLIC_REVALIDATE;
