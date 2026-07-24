"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Media,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { VAULT_DEFINITION } from "@/lib/vault-copy";
import { fetchMyVaultItems, fetchMyVaultPurchases } from "@/lib/vault-api";
import type { VaultItem, VaultPurchase } from "@/lib/types/vault";

/**
 * Buyer Vault item detail — only shows unlocked content the user can access.
 * Locked bodies are never fetched for items without access.
 */
export default function DashboardVaultItemPage() {
  const params = useParams<{ itemId: string }>();
  const [item, setItem] = useState<VaultItem | null>(null);
  const [purchase, setPurchase] = useState<VaultPurchase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [items, purchases] = await Promise.all([
          fetchMyVaultItems(),
          fetchMyVaultPurchases(),
        ]);
        if (!active) return;
        const found = items.find((row) => row.id === params.itemId) ?? null;
        setItem(found);
        setPurchase(
          purchases.find((p) => p.vault_item_id === params.itemId) ?? null,
        );
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load Vault item");
        }
      } finally {
        if (active) setLoaded(true);
      }
    })();
    return () => {
      active = false;
    };
  }, [params.itemId]);

  const publicHref =
    item?.host_username && item.slug
      ? `/@${item.host_username}/vault/${item.slug}`
      : null;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Vault"
      title={item?.title || "Vault unlock"}
      description={VAULT_DEFINITION}
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/vault">
            <Button size="sm" variant="ghost">
              My unlocks
            </Button>
          </Link>
          {publicHref ? (
            <Link href={publicHref}>
              <Button size="sm" variant="secondary">
                Public page
              </Button>
            </Link>
          ) : null}
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Could not load item">
          {error}
        </Alert>
      ) : null}

      {!loaded && !error ? <SkeletonLoader lines={6} /> : null}

      {loaded && !item && !error ? (
        <EmptyState
          title="No access to this Vault item"
          description={
            purchase
              ? `Purchase status: ${purchase.status}. Access is re-checked server-side — if payment is still pending, finish checkout from the host Vault.`
              : "This drop is not in your unlocked library. Unlock it from the host’s public Vault."
          }
          action={
            <Link href="/dashboard/vault">
              <Button variant="secondary">Back to My Vault</Button>
            </Link>
          }
        />
      ) : null}

      {item ? (
        <div className="mx-auto max-w-2xl space-y-6">
          <div className="relative aspect-[16/10] overflow-hidden rounded-[var(--radius-xl)] bg-ink">
            {item.cover_url ? (
              <Media src={item.cover_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <div className="padeya-hero-glow absolute inset-0" />
            )}
            <div className="absolute left-3 top-3">
              <Badge tone="accent">Unlocked</Badge>
            </div>
          </div>

          <Card className="space-y-4">
            <div className="space-y-2">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                {item.content_type.replace(/_/g, " ")}
                {item.host_display_name ? ` · ${item.host_display_name}` : ""}
              </p>
              <h2 className="text-2xl font-extrabold tracking-tight text-foreground">
                {item.title}
              </h2>
              {item.preview_text ? (
                <p className="text-base text-muted-foreground">{item.preview_text}</p>
              ) : null}
            </div>

            {item.description ? (
              <p className="text-sm text-muted-foreground">{item.description}</p>
            ) : null}
            {item.body ? (
              <p className="whitespace-pre-wrap text-base leading-relaxed text-muted-foreground">
                {item.body}
              </p>
            ) : null}
            {item.file_url ? (
              <a
                className="inline-block text-base font-bold text-foreground underline-offset-2 hover:underline"
                href={item.file_url}
                target="_blank"
                rel="noreferrer"
              >
                Download file
              </a>
            ) : null}
            {item.external_url ? (
              <a
                className="inline-block text-base font-bold text-foreground underline-offset-2 hover:underline"
                href={item.external_url}
                target="_blank"
                rel="noreferrer"
              >
                Open external link
              </a>
            ) : null}

            <ul className="space-y-3">
              {(item.media || [])
                .filter((m) => m.url)
                .map((m) => (
                  <li key={m.id}>
                    <a
                      className="text-base font-bold text-foreground underline-offset-2 hover:underline"
                      href={m.url!}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {m.label || m.media_type}
                    </a>
                  </li>
                ))}
            </ul>

            {publicHref ? (
              <Link href={publicHref}>
                <Button variant="secondary" size="sm">
                  Open on host Vault
                </Button>
              </Link>
            ) : null}
          </Card>
        </div>
      ) : null}
    </DashboardShell>
  );
}
