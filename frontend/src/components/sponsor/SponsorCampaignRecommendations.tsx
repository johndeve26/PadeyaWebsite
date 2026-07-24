"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { SponsorSaveButton } from "@/components/sponsor/SponsorSaveButton";
import { Alert, Button } from "@/components/ui";
import {
  SPONSORSHIP_MARKETPLACE_PATH,
  SPONSORSHIP_OPEN_SLOTS_HASH,
} from "@/lib/sponsor-marketplace-paths";
import { formatNgn } from "@/lib/format";
import { saveSponsorItem } from "@/lib/sponsor-saved-api";
import {
  addSavedItemToCampaign,
  fetchCampaignRecommendations,
  sendCampaignRecommendationFeedback,
  type CampaignRecommendation,
} from "@/lib/sponsor-campaigns-api";

export function SponsorCampaignRecommendations({
  sponsorId,
  campaignId,
  canEdit,
}: {
  sponsorId: string;
  campaignId: string;
  canEdit: boolean;
}) {
  const [items, setItems] = useState<CampaignRecommendation[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchCampaignRecommendations(sponsorId, campaignId);
    setItems(data.items);
  }, [campaignId, sponsorId]);

  useEffect(() => {
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(
          err instanceof ApiError ? err.detail : "Failed to load recommendations",
        );
      }
    })();
  }, [load]);

  async function feedback(
    item: CampaignRecommendation,
    action: string,
  ): Promise<void> {
    try {
      await sendCampaignRecommendationFeedback(
        sponsorId,
        campaignId,
        item.item_id,
        { item_type: item.item_type, action },
      );
      if (action === "dismissed" || action === "not_interested") {
        setItems((prev) => prev.filter((i) => i.item_id !== item.item_id));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Feedback failed");
    }
  }

  if (error) {
    return (
      <Alert tone="danger" title="Recommendations">
        {error}
      </Alert>
    );
  }

  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No recommended opportunities yet. Publish sponsorship slots from verified hosts
        appear here when they match your campaign rules.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li
          key={`${item.item_type}-${item.item_id}`}
          className="rounded-xl border border-border bg-card p-4 shadow-sm"
        >
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                {item.item_type.replace("_", " ")}
                {item.score_label ? ` · ${item.score_label}` : null}
              </p>
              {item.available && item.href ? (
                <Link href={item.href} className="text-lg font-bold text-accent">
                  {item.title ?? "Opportunity"}
                </Link>
              ) : (
                <p className="font-bold">{item.title ?? "Opportunity"}</p>
              )}
              {item.subtitle ? (
                <p className="text-sm text-muted-foreground">{item.subtitle}</p>
              ) : null}
              {item.host_display_name ? (
                <p className="text-sm text-muted-foreground">{item.host_display_name}</p>
              ) : null}
              {item.slot_price != null ? (
                <p className="text-sm">{formatNgn(item.slot_price)}</p>
              ) : null}
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {item.reasons.map((r) => (
              <span
                key={r.code}
                className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
              >
                {r.label}
              </span>
            ))}
          </div>
          {canEdit ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {item.item_type === "sponsorship_slot" ? (
                <Link href={`${SPONSORSHIP_MARKETPLACE_PATH}${SPONSORSHIP_OPEN_SLOTS_HASH}`}>
                  <Button size="sm" variant="secondary">
                    Send inquiry
                  </Button>
                </Link>
              ) : null}
              {item.item_type !== "sponsorship_slot" ? (
                <SponsorSaveButton
                  itemType={item.item_type as "host" | "event" | "sponsorship_slot"}
                  itemId={item.item_id}
                />
              ) : null}
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  void (async () => {
                    const saved = await saveSponsorItem(sponsorId, {
                      item_type: item.item_type as
                        | "host"
                        | "event"
                        | "sponsorship_slot",
                      item_id: item.item_id,
                    });
                    await addSavedItemToCampaign(
                      sponsorId,
                      campaignId,
                      saved.id,
                    );
                    await feedback(item, "saved");
                  })()
                }
              >
                Add to campaign
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => void feedback(item, "dismissed")}
              >
                Dismiss
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => void feedback(item, "not_interested")}
              >
                Not interested
              </Button>
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
