"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { VaultPreviewPanel } from "@/components/vault/studio/VaultPreviewPanel";
import { VaultStudioShell } from "@/components/vault/studio/VaultStudioShell";
import { Alert, Button, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchHostVaultItem,
  previewHostVaultItemAsFan,
} from "@/lib/vault-api";
import type { VaultItem } from "@/lib/types/vault";

export default function VaultItemPreviewPage() {
  const params = useParams<{ id: string }>();
  const [fanView, setFanView] = useState<VaultItem | null>(null);
  const [ownerView, setOwnerView] = useState<VaultItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"fan" | "owner">("fan");

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [fan, owner] = await Promise.all([
          previewHostVaultItemAsFan(params.id),
          fetchHostVaultItem(params.id),
        ]);
        if (!active) return;
        setFanView(fan);
        setOwnerView(owner);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Unable to load preview");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  const item = mode === "fan" ? fanView : ownerView;

  return (
    <VaultStudioShell
      title="Vault preview"
      description="Compare the locked fan view with your full owner view. Locked body and private media never leak."
      actions={
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant={mode === "fan" ? "primary" : "secondary"}
            onClick={() => setMode("fan")}
          >
            Fan (locked)
          </Button>
          <Button
            size="sm"
            variant={mode === "owner" ? "primary" : "secondary"}
            onClick={() => setMode("owner")}
          >
            Owner
          </Button>
          <Link href={`/host/vault/${params.id}/edit`}>
            <Button size="sm" variant="ghost">
              Edit
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

      {item ? (
        <div className="mx-auto max-w-2xl space-y-3">
          <VaultPreviewPanel item={item} mode={mode} />
          {mode === "fan" ? (
            <p className="text-sm text-muted-foreground">
              Fan preview never returns locked body or private media URLs.
            </p>
          ) : null}
        </div>
      ) : !error ? (
        <SkeletonLoader lines={8} />
      ) : null}
    </VaultStudioShell>
  );
}
