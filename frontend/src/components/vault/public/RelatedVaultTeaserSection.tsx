"use client";

import Link from "next/link";

import { PublicVaultItemCard } from "@/components/vault/public/PublicVaultItemCard";
import { Button, SectionHeader } from "@/components/ui";
import type { VaultCatalogCard } from "@/lib/types/vault";

type Props = {
  items: VaultCatalogCard[];
  username: string;
  hostId?: string | null;
  sourcePage?: string;
  listContext?: string;
  eyebrow?: string;
  title: string;
  description: string;
  vaultHref?: string;
  ctaLabel?: string;
};

export function RelatedVaultTeaserSection({
  items,
  username,
  hostId = null,
  sourcePage = "related_vault",
  listContext = "related_vault",
  eyebrow = "Vault",
  title,
  description,
  vaultHref,
  ctaLabel = "Open Vault",
}: Props) {
  if (items.length === 0) return null;

  const href = vaultHref || `/u/${username}/vault`;

  return (
    <section className="space-y-5">
      <SectionHeader eyebrow={eyebrow} title={title} description={description} />
      <div className="grid gap-4 sm:grid-cols-2">
        {items.map((item, index) => (
          <PublicVaultItemCard
            key={item.id}
            item={item}
            username={item.host_username || username}
            hostId={hostId}
            sourcePage={sourcePage}
            listContext={listContext}
            cardPosition={index}
          />
        ))}
      </div>
      <Link href={href}>
        <Button variant="secondary">{ctaLabel}</Button>
      </Link>
    </section>
  );
}
