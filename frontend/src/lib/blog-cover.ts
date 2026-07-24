/** Category-aware cover resolution for blog cards and heroes. */

import type { BlogCategory } from "@/lib/blog-api";
import { brand } from "@/lib/brand";

const GENERIC_COVERS = new Set([
  "/brand/padeya-hero.jpg",
  brand.heroImage,
]);

/** Browse SVGs used as category placeholders (varied, on-brand). */
const CATEGORY_PLACEHOLDERS: Record<string, string> = {
  discovery: "/brand/browse/nightlife.svg",
  "event-planning": "/brand/browse/comedy.svg",
  "host-growth": "/brand/browse/music.svg",
  safety: "/brand/browse/tech.svg",
  fans: "/brand/browse/campus.svg",
  product: "/brand/browse/arts-culture.svg",
  merch: "/brand/browse/food-drink.svg",
};

const CATEGORY_GRADIENTS: Record<string, string> = {
  discovery: `radial-gradient(ellipse at 25% 20%, ${brand.colors.green}40, transparent 55%), linear-gradient(135deg, #0a0a0a 0%, #12200a 100%)`,
  "event-planning": `radial-gradient(ellipse at 70% 30%, ${brand.colors.green}28, transparent 50%), linear-gradient(145deg, #0a0a0a, #1a1208)`,
  "host-growth": `radial-gradient(ellipse at 40% 10%, ${brand.colors.green}35, transparent 52%), linear-gradient(160deg, #050505, #101810)`,
  safety: `radial-gradient(ellipse at 20% 80%, ${brand.colors.green}22, transparent 48%), linear-gradient(180deg, #0a0a0a, #0e1418)`,
  fans: `radial-gradient(ellipse at 80% 20%, ${brand.colors.green}30, transparent 50%), linear-gradient(120deg, #0a0a0a, #14100a)`,
  product: `radial-gradient(ellipse at 50% 0%, ${brand.colors.green}26, transparent 55%), linear-gradient(200deg, #000, #121212)`,
  merch: `radial-gradient(ellipse at 15% 40%, ${brand.colors.green}32, transparent 50%), linear-gradient(90deg, #0a0a0a, #16120a)`,
};

export function isGenericBlogCover(url?: string | null): boolean {
  if (!url) return true;
  return GENERIC_COVERS.has(url.split("?")[0] ?? url);
}

export function blogCategoryPlaceholder(
  category?: BlogCategory | null,
): string {
  const slug = category?.slug ?? "";
  return CATEGORY_PLACEHOLDERS[slug] ?? "/brand/browse/nightlife.svg";
}

export function blogCategoryGradient(
  category?: BlogCategory | null,
): string {
  const slug = category?.slug ?? "";
  return (
    CATEGORY_GRADIENTS[slug] ??
    `radial-gradient(ellipse at 30% 20%, ${brand.colors.green}33, transparent 50%), #0a0a0a`
  );
}

/**
 * Prefer a real unique cover; fall back to category art when missing/generic
 * so related rails never repeat the same hero image.
 */
export function resolveBlogCoverUrl(
  coverUrl: string | null | undefined,
  category?: BlogCategory | null,
): { src: string | null; isPlaceholder: boolean } {
  if (coverUrl && !isGenericBlogCover(coverUrl)) {
    return { src: coverUrl, isPlaceholder: false };
  }
  return {
    src: blogCategoryPlaceholder(category),
    isPlaceholder: true,
  };
}

export function blogCoverAlt(
  title: string,
  category?: BlogCategory | null,
): string {
  if (category?.name) return `${title} — ${category.name} on ${brand.name}`;
  return `${title} — ${brand.name} blog`;
}
