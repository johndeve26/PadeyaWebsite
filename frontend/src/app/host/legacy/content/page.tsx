"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { LegacyContentBlockManager } from "@/components/legacy/studio/LegacyContentBlockManager";
import { LegacyFeaturedItemPicker } from "@/components/legacy/studio/LegacyFeaturedItemPicker";
import { LegacyStudioShell } from "@/components/legacy/studio/LegacyStudioShell";
import { Alert, Button, Card, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMyLegacyPage } from "@/lib/legacy-api";
import type { LegacyPage, LegacyVaultPreviewCard } from "@/lib/types/legacy";
import { VAULT_LEGACY_BLOCK_DESCRIPTION } from "@/lib/vault-copy";
import { fetchHostVaultItems } from "@/lib/vault-api";

export default function HostLegacyContentPage() {
  const [page, setPage] = useState<LegacyPage | null>(null);
  const [vaultItems, setVaultItems] = useState<LegacyVaultPreviewCard[]>([]);
  const [publishedVaultItems, setPublishedVaultItems] = useState<
    LegacyVaultPreviewCard[]
  >([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [data, hostVault] = await Promise.all([
      fetchMyLegacyPage(),
      fetchHostVaultItems().catch(() => []),
    ]);
    setPage(data);
    // Feature picker needs all host drops (not only the public preview limit).
    const fromHost = hostVault
      .filter(
        (v) =>
          !["archived", "hidden_by_admin", "disabled"].includes(v.status) &&
          v.moderation_status !== "removed",
      )
      .map(
        (v): LegacyVaultPreviewCard => ({
          id: v.id,
          title: `${v.title}${v.status !== "published" ? ` (${v.status})` : ""}`,
          slug: v.slug,
          cover_url: v.cover_url,
          preview_text: v.preview_text,
          locked: v.locked,
          has_access: v.has_access,
          content_type: v.content_type,
          price: v.price,
          currency: v.currency,
          share_path: v.host_username
            ? `/u/${v.host_username}/vault/${v.slug}`
            : `/u/${v.host_id}/vault/${v.slug}`,
        }),
      );
    const previewIds = new Set(fromHost.map((v) => v.id));
    const extras = (data.vault_preview ?? []).filter((v) => !previewIds.has(v.id));
    setVaultItems([...fromHost, ...extras]);
    setPublishedVaultItems(
      hostVault
        .filter(
          (v) =>
            v.status === "published" &&
            v.moderation_status !== "removed" &&
            v.moderation_status !== "hidden",
        )
        .map(
          (v): LegacyVaultPreviewCard => ({
            id: v.id,
            title: v.title,
            slug: v.slug,
            cover_url: v.cover_url,
            preview_text: v.preview_text,
            locked: true,
            has_access: false,
            content_type: v.content_type,
            price: v.price,
            currency: v.currency,
            share_path: v.host_username
              ? `/u/${v.host_username}/vault/${v.slug}`
              : `/u/${v.host_id}/vault/${v.slug}`,
          }),
        ),
    );
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Unable to load content studio");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  const vaultBlockVisible = useMemo(
    () =>
      (page?.content_blocks ?? []).some(
        (b) => b.block_type === "vault_preview" && b.is_visible,
      ),
    [page?.content_blocks],
  );

  return (
    <LegacyStudioShell
      title="Content blocks"
      description="Choose what visitors see on your public Legacy Page — order, visibility, featured items, and Vault Preview."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/host/vault">
            <Button size="sm" variant="ghost">
              Vault studio
            </Button>
          </Link>
          <Link href="/host/legacy/preview">
            <Button size="sm" variant="secondary">
              Preview
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Unable to load">
          {error}
        </Alert>
      ) : null}

      {page ? (
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-6">
            <Card className="space-y-2">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                Vault Preview block
              </p>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {VAULT_LEGACY_BLOCK_DESCRIPTION} In the Vault Preview block below, set
                title and description, choose automatic or manual source, pick layout,
                and select which drops appear. Feature a drop in the sidebar to pin it
                first on the public page.
              </p>
              <p className="text-sm font-semibold text-foreground">
                Block status: {vaultBlockVisible ? "Visible" : "Hidden"}
              </p>
              {vaultItems.length === 0 ? (
                <Link
                  href="/host/vault/new"
                  className="inline-block text-sm font-semibold text-foreground underline-offset-2 hover:underline"
                >
                  Create a Vault drop →
                </Link>
              ) : (
                <Link
                  href="/host/vault/preview"
                  className="inline-block text-sm font-semibold text-foreground underline-offset-2 hover:underline"
                >
                  Preview public Vault →
                </Link>
              )}
            </Card>
            <LegacyContentBlockManager
              initialBlocks={page.content_blocks ?? []}
              vaultItems={publishedVaultItems}
              onChange={(blocks) => setPage({ ...page, content_blocks: blocks })}
            />
          </div>
          <LegacyFeaturedItemPicker
            featured={page.featured_items ?? []}
            upcoming={page.upcoming_events}
            past={page.past_events}
            reviews={page.reviews}
            vault={vaultItems}
            memories={page.event_memories ?? []}
            onUpdated={() => void load().catch(() => undefined)}
          />
        </div>
      ) : !error ? (
        <SkeletonLoader lines={10} />
      ) : null}
    </LegacyStudioShell>
  );
}
