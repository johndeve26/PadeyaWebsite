import type { CSSProperties } from "react";

import type { MerchCatalogProduct } from "@/lib/types/merch";

const TYPE_MARKS: Record<string, string> = {
  t_shirt: "TEE",
  tee: "TEE",
  shirt: "TEE",
  cap: "CAP",
  hat: "CAP",
  bucket_hat: "CAP",
  hoodie: "HOODIE",
  face_mask: "MASK",
  mask: "MASK",
  wristband: "WRISTBAND",
  poster: "POSTER",
  tote_bag: "TOTE",
  tote: "TOTE",
  notebook: "NOTE",
  vip_pack: "VIP",
  souvenir: "SOUVENIR",
  other: "MERCH",
};

/** Short mark for premium image fallbacks. */
export function merchTypeMark(productType?: string | null): string {
  if (!productType) return "MERCH";
  const key = productType.toLowerCase().replace(/\s+/g, "_");
  return TYPE_MARKS[key] || "MERCH";
}

/** Infer mark from product name first (demo polish), then product_type. */
export function inferMerchTypeMark(product: {
  product_type?: string | null;
  name?: string | null;
}): string {
  const n = (product.name || "").toLowerCase();
  if (n.includes("hoodie")) return "HOODIE";
  if (n.includes("wristband")) return "WRISTBAND";
  if (n.includes("poster")) return "POSTER";
  if (n.includes("tote")) return "TOTE";
  if (n.includes("mask")) return "MASK";
  if (n.includes("notebook") || n.includes("builder")) return "NOTE";
  if (n.includes("cap") || n.includes("bucket hat") || n.includes(" hat"))
    return "CAP";
  if (
    n.includes("tee") ||
    n.includes("t-shirt") ||
    n.includes("t shirt") ||
    /\bshirt\b/.test(n)
  )
    return "TEE";
  if (product.product_type) {
    const fromType = merchTypeMark(product.product_type);
    if (fromType !== "MERCH") return fromType;
  }
  return "MERCH";
}

/** Deterministic accent gradient for placeholder visuals (local-only styling). */
export function merchPlaceholderStyle(product: {
  product_type?: string | null;
  name?: string | null;
  category?: string | null;
}): CSSProperties {
  const seed =
    product.category ||
    product.product_type ||
    product.name ||
    "merch";
  const palettes: [string, string][] = [
    ["color-mix(in srgb, var(--primary) 22%, var(--surface-muted))", "var(--card)"],
    ["color-mix(in srgb, #3d5a45 28%, var(--surface-muted))", "var(--ink)"],
    ["color-mix(in srgb, #5c4d7a 24%, var(--surface-muted))", "var(--card)"],
    ["color-mix(in srgb, #8b5a2b 22%, var(--surface-muted))", "var(--ink)"],
    ["color-mix(in srgb, #2f6f7e 26%, var(--surface-muted))", "var(--card)"],
    ["color-mix(in srgb, #7a3d4a 20%, var(--surface-muted))", "var(--ink)"],
    ["color-mix(in srgb, #4a6741 24%, var(--surface-muted))", "var(--card)"],
    ["color-mix(in srgb, #6b5b2f 22%, var(--surface-muted))", "var(--ink)"],
  ];
  let hash = 0;
  const key = seed.toLowerCase();
  for (let i = 0; i < key.length; i += 1) {
    hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  }
  const [from, to] = palettes[hash % palettes.length];
  return {
    backgroundImage: `radial-gradient(ellipse at top right, color-mix(in srgb, var(--primary) 16%, transparent), transparent 55%), linear-gradient(155deg, ${from}, ${to})`,
  };
}

export function productImageUrl(
  product: Pick<MerchCatalogProduct, "cover_image_url" | "image_url">,
): string | null {
  return product.cover_image_url || product.image_url || null;
}
