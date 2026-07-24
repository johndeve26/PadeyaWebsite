"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { VaultPreviewPanel } from "@/components/vault/studio/VaultPreviewPanel";
import { VaultStudioShell } from "@/components/vault/studio/VaultStudioShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import {
  archiveHostVaultItem,
  fetchHostVaultItem,
  fetchVaultStudio,
} from "@/lib/vault-api";
import type { VaultItem } from "@/lib/types/vault";

export default function HostVaultItemDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [item, setItem] = useState<VaultItem | null>(null);
  const [featured, setFeatured] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [row, studio] = await Promise.all([
          fetchHostVaultItem(params.id),
          fetchVaultStudio().catch(() => null),
        ]);
        if (!active) return;
        setItem(row);
        setFeatured(studio?.featured_vault_item_id === row.id);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load drop");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  async function onArchive() {
    if (!confirm("Archive this drop? It will disappear from the public Vault.")) return;
    setBusy(true);
    setError(null);
    try {
      await archiveHostVaultItem(params.id);
      router.push("/host/vault");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Archive failed");
      setBusy(false);
    }
  }

  return (
    <VaultStudioShell
      title={item?.title || "Vault drop"}
      description="Host detail for this exclusive drop — edit access, preview fan lock, or feature it on Legacy."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href={`/host/vault/${params.id}/edit`}>
            <Button size="sm">Edit</Button>
          </Link>
          <Link href={`/host/vault/${params.id}/preview`}>
            <Button size="sm" variant="secondary">
              Fan preview
            </Button>
          </Link>
          <Link href="/host/vault">
            <Button size="sm" variant="ghost">
              Studio
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      {!item && !error ? <SkeletonLoader lines={8} /> : null}

      {item ? (
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
          <VaultPreviewPanel item={item} mode="owner" />
          <div className="space-y-4">
            <Card className="space-y-3">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                Status
              </p>
              <div className="flex flex-wrap gap-2">
                <StatusBadge status={item.status} />
                <Badge tone="dark">
                  {(item.access?.access_type || "free").replace(/_/g, " ")}
                </Badge>
                {featured ? <Badge tone="accent">Legacy featured</Badge> : null}
              </div>
              <p className="text-sm capitalize text-muted-foreground">
                {item.content_type.replace(/_/g, " ")}
                {Number(item.price) > 0 ? ` · ${formatNgn(Number(item.price))}` : ""}
              </p>
            </Card>

            <Card className="space-y-3">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                Routes
              </p>
              <div className="flex flex-col gap-2">
                <Link href={`/host/vault/${item.id}/edit`}>
                  <Button size="sm" className="w-full">
                    Edit drop
                  </Button>
                </Link>
                <Link href={`/host/vault/${item.id}/preview`}>
                  <Button size="sm" variant="secondary" className="w-full">
                    Fan vs owner preview
                  </Button>
                </Link>
                <Link href="/host/legacy/content">
                  <Button size="sm" variant="secondary" className="w-full">
                    Feature on Legacy
                  </Button>
                </Link>
                {item.host_username ? (
                  <Link href={`/@${item.host_username}/vault/${item.slug}`}>
                    <Button size="sm" variant="ghost" className="w-full">
                      Open public page
                    </Button>
                  </Link>
                ) : null}
              </div>
            </Card>

            {item.status !== "archived" && item.status !== "hidden_by_admin" ? (
              <Button
                size="sm"
                variant="ghost"
                className="text-danger"
                disabled={busy}
                onClick={() => void onArchive()}
              >
                Archive drop
              </Button>
            ) : null}
          </div>
        </div>
      ) : null}
    </VaultStudioShell>
  );
}
