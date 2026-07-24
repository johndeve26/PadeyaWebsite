"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  VaultItemEditor,
  valuesFromItem,
  type VaultItemEditorValues,
} from "@/components/vault/studio/VaultItemEditor";
import { VaultStudioShell } from "@/components/vault/studio/VaultStudioShell";
import { Alert, Button, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  archiveHostVaultItem,
  deleteHostVaultItem,
  fetchHostVaultItem,
  fetchVaultStudio,
  updateHostVaultItem,
} from "@/lib/vault-api";

export default function EditVaultItemPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [initial, setInitial] = useState<VaultItemEditorValues | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [item, studio] = await Promise.all([
          fetchHostVaultItem(params.id),
          fetchVaultStudio().catch(() => null),
        ]);
        if (!active) return;
        const values = valuesFromItem(item);
        values.feature_on_legacy = studio?.featured_vault_item_id === item.id;
        setInitial(values);
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

  async function onDelete() {
    if (
      !confirm(
        "Permanently delete this draft? Only drafts with no unlock/purchase history can be deleted — otherwise archive.",
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deleteHostVaultItem(params.id);
      router.push("/host/vault");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Delete failed");
      setBusy(false);
    }
  }

  return (
    <VaultStudioShell
      title="Edit Vault drop"
      description="Update access rules, media, publish status, and Legacy featuring."
      actions={
        <div className="flex flex-wrap gap-2">
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

      {!initial && !error ? <SkeletonLoader lines={8} /> : null}

      {initial ? (
        <VaultItemEditor
          key={`${params.id}-${initial.slug}-${initial.feature_on_legacy}`}
          mode="edit"
          itemId={params.id}
          initial={initial}
          submitLabel="Save drop"
          onSubmit={(payload) => updateHostVaultItem(params.id, payload)}
          secondaryActions={
            <>
              <Button
                type="button"
                variant="secondary"
                disabled={busy}
                onClick={() => void onArchive()}
              >
                Archive
              </Button>
              <Button
                type="button"
                variant="ghost"
                disabled={busy}
                onClick={() => void onDelete()}
              >
                Delete
              </Button>
            </>
          }
        />
      ) : null}
    </VaultStudioShell>
  );
}
