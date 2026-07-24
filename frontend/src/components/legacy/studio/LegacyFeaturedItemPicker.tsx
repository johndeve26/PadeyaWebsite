"use client";

import Link from "next/link";
import { useState } from "react";

import { Alert, Button, Card } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  clearLegacyFeaturedPlacement,
  upsertLegacyFeaturedItem,
} from "@/lib/legacy-api";
import type {
  LegacyEventCard,
  LegacyFeaturedItem,
  LegacyMemoryCard,
  LegacyVaultPreviewCard,
  VerifiedReview,
} from "@/lib/types/legacy";

type Props = {
  featured: LegacyFeaturedItem[];
  upcoming: LegacyEventCard[];
  past: LegacyEventCard[];
  reviews: VerifiedReview[];
  vault: LegacyVaultPreviewCard[];
  memories: LegacyMemoryCard[];
  onUpdated: () => void;
};

const PLACEMENTS = [
  {
    placement: "featured_upcoming_event",
    label: "Featured upcoming event",
    itemType: "event",
  },
  {
    placement: "featured_past_event",
    label: "Featured past event",
    itemType: "event",
  },
  {
    placement: "featured_review",
    label: "Featured review",
    itemType: "review",
  },
  {
    placement: "featured_vault_item",
    label: "Featured Vault item",
    itemType: "vault_item",
  },
  {
    placement: "featured_memory",
    label: "Featured event memory",
    itemType: "memory",
  },
] as const;

export function LegacyFeaturedItemPicker({
  featured,
  upcoming,
  past,
  reviews,
  vault,
  memories,
  onUpdated,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const row of featured) {
      map[row.placement] = row.item_id;
    }
    return map;
  });

  function optionsFor(itemType: string, placement: string) {
    if (itemType === "event" && placement.includes("upcoming")) {
      return upcoming.map((e) => ({ id: e.id, label: e.title }));
    }
    if (itemType === "event") {
      return past.map((e) => ({ id: e.id, label: e.title }));
    }
    if (itemType === "review") {
      return reviews.map((r) => ({
        id: r.id,
        label: `${r.rating}★ ${r.title || r.event_title || "Review"}`,
      }));
    }
    if (itemType === "vault_item") {
      return vault.map((v) => ({ id: v.id, label: v.title }));
    }
    return memories.map((m) => ({ id: m.id, label: m.event_title }));
  }

  async function save(placement: string, itemType: string) {
    const itemId = values[placement];
    setBusy(true);
    setError(null);
    try {
      if (!itemId) {
        await clearLegacyFeaturedPlacement(placement);
      } else {
        await upsertLegacyFeaturedItem({
          placement,
          item_type: itemType,
          item_id: itemId,
        });
      }
      onUpdated();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Unable to save featured item");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="space-y-4">
      <div>
        <h3 className="text-lg font-extrabold text-foreground">Featured items</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Pin the event, review, Vault drop, or memory that leads your Legacy Page.
          Featured Vault items appear first in the public Vault Preview block.
        </p>
      </div>
      {error ? (
        <Alert tone="danger" title="Featured items">
          {error}
        </Alert>
      ) : null}
      {vault.length === 0 ? (
        <Alert tone="info" title="No Vault drops yet">
          Create a drop in{" "}
          <Link href="/host/vault/new" className="font-semibold underline">
            Vault studio
          </Link>{" "}
          to feature exclusive content on Legacy.
        </Alert>
      ) : null}
      <div className="space-y-4">
        {PLACEMENTS.map((row) => {
          const options = optionsFor(row.itemType, row.placement);
          return (
            <div key={row.placement} className="space-y-2">
              <label className="text-sm font-semibold text-foreground">
                {row.label}
              </label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <select
                  className="w-full flex-1 rounded-[var(--radius-md)] border border-input-border bg-input-background px-3 py-2 text-sm text-input-foreground"
                  value={values[row.placement] ?? ""}
                  disabled={busy}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, [row.placement]: e.target.value }))
                  }
                >
                  <option value="">Not featured</option>
                  {options.map((opt) => (
                    <option key={opt.id} value={opt.id}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy || options.length === 0}
                  onClick={() => void save(row.placement, row.itemType)}
                >
                  Save
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
