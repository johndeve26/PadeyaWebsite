"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { useOptionalSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import { Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchSponsorSaved,
  saveSponsorItem,
  savedKey,
  unsaveSponsorItem,
} from "@/lib/sponsor-saved-api";
import { fetchSponsorWorkspaces } from "@/lib/sponsor-profiles-api";

type Props = {
  itemType: "host" | "event" | "sponsorship_slot";
  itemId: string;
  className?: string;
  size?: "sm" | "md";
};

export function useSponsorSavedMap(sponsorId: string | null) {
  const [map, setMap] = useState<Map<string, string>>(new Map());
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!sponsorId) {
      setMap(new Map());
      return;
    }
    setLoading(true);
    try {
      const data = await fetchSponsorSaved(sponsorId);
      const next = new Map<string, string>();
      for (const row of data.items) {
        next.set(savedKey(row.item_type, row.item_id), row.id);
      }
      setMap(next);
    } catch {
      setMap(new Map());
    } finally {
      setLoading(false);
    }
  }, [sponsorId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { map, loading, refresh };
}

export function SponsorSaveButton({
  itemType,
  itemId,
  className = "",
  size = "sm",
}: Props) {
  const { user } = useAuth();
  const sponsorCtx = useOptionalSponsorWorkspace();
  const [fallback, setFallback] = useState<{
    sponsor_id: string;
    is_owner: boolean;
    role: string;
  } | null>(null);

  useEffect(() => {
    if (!user || sponsorCtx?.active) return;
    void fetchSponsorWorkspaces()
      .then((rows) => {
        if (rows[0]) {
          setFallback({
            sponsor_id: rows[0].sponsor_id,
            is_owner: rows[0].is_owner,
            role: rows[0].role,
          });
        }
      })
      .catch(() => setFallback(null));
  }, [user, sponsorCtx?.active]);

  const active = sponsorCtx?.active ?? fallback;
  const sponsorId = active?.sponsor_id ?? null;
  const canSave =
    Boolean(user) &&
    Boolean(sponsorId) &&
    (active?.is_owner ||
      active?.role === "admin" ||
      active?.role === "campaign_manager");

  const { map, refresh } = useSponsorSavedMap(sponsorId);
  const key = savedKey(itemType, itemId);
  const savedId = map.get(key);
  const [busy, setBusy] = useState(false);

  if (!user || !sponsorId) return null;

  async function toggle() {
    if (!sponsorId || !canSave) return;
    setBusy(true);
    try {
      if (savedId) {
        await unsaveSponsorItem(sponsorId, savedId);
      } else {
        await saveSponsorItem(sponsorId, {
          item_type: itemType,
          item_id: itemId,
        });
      }
      await refresh();
    } catch (err) {
      console.error(err instanceof ApiError ? err.detail : err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button
      type="button"
      size={size}
      variant={savedId ? "secondary" : "ghost"}
      className={className}
      disabled={busy || !canSave}
      title={
        !canSave
          ? "Viewers can browse saved items but not save"
          : savedId
            ? "Remove from saved"
            : "Save to sponsor workspace"
      }
      onClick={() => void toggle()}
    >
      {savedId ? "Saved" : "Save"}
    </Button>
  );
}
