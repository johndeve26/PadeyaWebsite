import type { MarketplaceHome, MarketplaceProduct } from "@/lib/types/merch";

export const MERCH_SECTION_LIMITS = {
  featured: 6,
  eventMerch: 8,
  drops: 4,
  vault: 4,
  hostShops: 6,
  catalogPage: 12,
} as const;

export type MerchDiscoveryTab =
  | "all"
  | "event_merch"
  | "host_shops"
  | "drops"
  | "vault"
  | "bundles";

export const MERCH_DISCOVERY_TABS: {
  id: MerchDiscoveryTab;
  label: string;
  sectionId?: string;
}[] = [
  { id: "all", label: "All" },
  { id: "event_merch", label: "Event merch", sectionId: "event-merch" },
  { id: "host_shops", label: "Host shops", sectionId: "host-shops" },
  { id: "drops", label: "Drops", sectionId: "drops" },
  { id: "vault", label: "Vault exclusives", sectionId: "vault" },
  { id: "bundles", label: "Bundles", sectionId: "catalog" },
];

export function productKey(product: MarketplaceProduct): string {
  return `${product.id}:${product.host_slug ?? product.host_id ?? ""}`;
}

/** Remove products already shown in prior sections (by id). */
export function excludeShown(
  products: MarketplaceProduct[],
  shown: Set<string>,
): MarketplaceProduct[] {
  return products.filter((p) => !shown.has(productKey(p)));
}

export function markShown(
  shown: Set<string>,
  products: MarketplaceProduct[],
): void {
  for (const p of products) shown.add(productKey(p));
}

export function limitProducts(
  products: MarketplaceProduct[],
  max: number,
): MarketplaceProduct[] {
  return products.slice(0, max);
}

export type CuratedMarketplaceHome = {
  featured: MarketplaceProduct[];
  eventMerch: MarketplaceProduct[];
  hostShops: MarketplaceHome["host_shops"];
  drops: MarketplaceProduct[];
  vault: MarketplaceProduct[];
};

/** Apply section limits and dedupe across adjacent curated rails. */
export function curateMarketplaceHome(home: MarketplaceHome): CuratedMarketplaceHome {
  const shown = new Set<string>();

  const featured = limitProducts(
    excludeShown(home.featured ?? [], shown),
    MERCH_SECTION_LIMITS.featured,
  );
  markShown(shown, featured);

  const eventMerch = limitProducts(
    excludeShown(home.event_merch ?? [], shown),
    MERCH_SECTION_LIMITS.eventMerch,
  );
  markShown(shown, eventMerch);

  // Dedicated home queries — do not strip drops/Vault because they appeared in featured.
  const drops = limitProducts(home.drops ?? [], MERCH_SECTION_LIMITS.drops);
  markShown(shown, drops);

  const vault = limitProducts(
    home.vault_exclusives ?? [],
    MERCH_SECTION_LIMITS.vault,
  );
  markShown(shown, vault);

  const hostShops = (home.host_shops ?? []).slice(0, MERCH_SECTION_LIMITS.hostShops);

  return { featured, eventMerch, hostShops, drops, vault };
}

export function dropEligibilityLabel(audience?: string | null): string | null {
  if (!audience) return null;
  const map: Record<string, string> = {
    checked_in: "Checked-in fans only",
    checked_in_attendee: "Checked-in fans only",
    ticket_buyers: "Ticket buyers only",
    ticket_holder: "Ticket buyers only",
    vip: "VIP only",
    vip_ticket_holder: "VIP only",
    vault_members: "Vault members only",
    paid_vault_member: "Vault members only",
    public: "Open drop",
  };
  return map[audience] ?? audience.replace(/_/g, " ");
}
