"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { VaultDefinitionNote } from "@/components/vault/VaultDefinitionNote";
import { VaultStudioShell } from "@/components/vault/studio/VaultStudioShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Media,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import { VAULT_PUBLIC_DESCRIPTION } from "@/lib/vault-copy";
import { fetchVaultStudio } from "@/lib/vault-api";
import type { VaultStudioSummary } from "@/lib/types/vault";

/**
 * Studio-level Vault preview — how published drops appear to fans,
 * plus Legacy Vault Preview block visibility.
 */
export default function HostVaultStudioPreviewPage() {
  const [studio, setStudio] = useState<VaultStudioSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchVaultStudio();
        if (active) setStudio(data);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Unable to load Vault preview");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const published =
    studio?.items.filter(
      (i) => i.status === "published" && i.moderation_status !== "removed",
    ) ?? [];

  return (
    <VaultStudioShell
      title="Vault preview"
      description="Fan-facing catalog of your published drops. Locked bodies stay protected — this mirrors what visitors see on your public Vault."
      actions={
        <div className="flex flex-wrap gap-2">
          {studio ? (
            <Link href={studio.share_path}>
              <Button size="sm">Open public Vault</Button>
            </Link>
          ) : null}
          <Link href="/host/legacy/preview">
            <Button size="sm" variant="secondary">
              Legacy preview
            </Button>
          </Link>
          <Link href="/host/legacy/content">
            <Button size="sm" variant="ghost">
              Feature on Legacy
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Preview unavailable">
          {error}
        </Alert>
      ) : null}

      {!studio && !error ? <SkeletonLoader lines={8} /> : null}

      {studio ? (
        <div className="space-y-8">
          <div className="relative overflow-hidden rounded-[var(--radius-xl)] bg-ink px-5 py-8 text-paper sm:px-8">
            <div aria-hidden className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-80" />
            <div className="relative space-y-4">
              <Badge tone="accent">Public Vault</Badge>
              <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">
                @{studio.host_username}&apos;s Vault
              </h2>
              <p className="max-w-xl text-sm leading-relaxed text-subtle-foreground sm:text-base">
                {VAULT_PUBLIC_DESCRIPTION}
              </p>
              <VaultDefinitionNote tone="dark" compact className="max-w-xl" />
              <div className="flex flex-wrap gap-3 text-sm text-subtle-foreground">
                <span>
                  Legacy Vault block:{" "}
                  <strong className="text-paper">
                    {studio.legacy_vault_block_visible ? "Visible" : "Hidden"}
                  </strong>
                </span>
                <span>·</span>
                <span>
                  {published.length} published drop
                  {published.length === 1 ? "" : "s"}
                </span>
              </div>
            </div>
          </div>

          {published.length === 0 ? (
            <EmptyState
              title="No published drops yet"
              description="Publish a drop to see it in the fan catalog preview."
              action={
                <Link href="/host/vault/new">
                  <Button>Create drop</Button>
                </Link>
              }
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {published.map((item) => {
                const isFeatured = studio.featured_vault_item_id === item.id;
                return (
                  <Card key={item.id} padded={false} className="overflow-hidden">
                    <div className="relative aspect-[16/10] bg-surface-dark">
                      {item.cover_url ? (
                        <Media
                          src={item.cover_url}
                          alt=""
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="padeya-hero-glow absolute inset-0" />
                      )}
                      <div className="absolute left-3 top-3 flex flex-wrap gap-2">
                        <Badge tone="accent">Locked teaser</Badge>
                        {isFeatured ? <Badge tone="dark">Legacy featured</Badge> : null}
                      </div>
                    </div>
                    <div className="space-y-3 p-4">
                      <div className="flex flex-wrap gap-2">
                        <StatusBadge status={item.status} />
                        <Badge tone="dark">
                          {(item.access?.access_type || "free").replace(/_/g, " ")}
                        </Badge>
                      </div>
                      <h3 className="text-lg font-extrabold text-foreground">
                        {item.title}
                      </h3>
                      <p className="line-clamp-2 text-sm text-muted-foreground">
                        {item.preview_text ||
                          "Preview text only — body and private media stay protected."}
                      </p>
                      {Number(item.price) > 0 ? (
                        <p className="text-sm font-bold text-foreground">
                          {formatNgn(Number(item.price))}
                        </p>
                      ) : null}
                      <div className="flex flex-wrap gap-2">
                        <Link href={`/host/vault/${item.id}`}>
                          <Button size="sm" variant="secondary">
                            Open drop
                          </Button>
                        </Link>
                        <Link href={`/host/vault/${item.id}/preview`}>
                          <Button size="sm" variant="ghost">
                            Fan lock
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      ) : null}
    </VaultStudioShell>
  );
}
