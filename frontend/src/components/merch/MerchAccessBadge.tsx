"use client";

import { Badge } from "@/components/ui";
import type { MerchCatalogProduct } from "@/lib/types/merch";

type Props = {
  product: MerchCatalogProduct;
  size?: "sm" | "md";
};

/** Compact access / exclusivity badges for cards and hero chips. */
export function MerchAccessBadge({ product, size = "sm" }: Props) {
  const badges: { key: string; label: string; tone: "accent" | "outline" | "dark" | "warning" }[] =
    [];

  if (product.is_vault_exclusive || product.requires_vault_access) {
    badges.push({ key: "vault", label: "Vault exclusive", tone: "accent" });
  }
  if (
    product.requires_ticket ||
    product.required_access_type === "ticket" ||
    product.required_access_type === "vip" ||
    product.required_access_type === "check_in"
  ) {
    badges.push({ key: "ticket", label: "Requires ticket", tone: "warning" });
  }
  if (product.is_post_event_drop) {
    badges.push({ key: "drop", label: "Post-event drop", tone: "outline" });
  }
  if (product.is_sponsor_branded) {
    badges.push({ key: "sponsor", label: "Sponsor-branded", tone: "accent" });
  }

  if (badges.length === 0) return null;

  return (
    <>
      {badges.map((b) => (
        <Badge key={b.key} tone={b.tone} size={size}>
          {b.label}
        </Badge>
      ))}
    </>
  );
}
