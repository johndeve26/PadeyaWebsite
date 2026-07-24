"use client";

import { type ReactNode } from "react";

import { Button } from "@/components/ui";
import type { EnrichedSponsorshipSlot } from "@/lib/sponsor-slot-presentation";

import { SponsorSaveButton } from "@/components/sponsor/SponsorSaveButton";
import { SponsorSlotCard } from "./SponsorSlotCard";

export const SPONSOR_SLOTS_PAGE_SIZE = 6;

export function SponsorshipSlotsGrid({
  slots,
  visibleCount,
  onShowMore,
  activeSlotId,
  onToggleInquiry,
  renderInquiryForm,
}: {
  slots: EnrichedSponsorshipSlot[];
  visibleCount: number;
  onShowMore: () => void;
  activeSlotId: string | null;
  onToggleInquiry: (slotId: string) => void;
  renderInquiryForm: (slot: EnrichedSponsorshipSlot) => ReactNode;
}) {
  const visible = slots.slice(0, visibleCount);
  const remaining = Math.max(slots.length - visibleCount, 0);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {`Showing ${visible.length} of ${slots.length} ${
          slots.length === 1 ? "slot" : "slots"
        }`}
      </p>

      <div className="grid gap-3 lg:grid-cols-2">
        {visible.map((slot) => (
          <SponsorSlotCard
            key={slot.id}
            slot={slot}
            compact
            inquiryOpen={activeSlotId === slot.id}
            onToggleInquiry={() => onToggleInquiry(slot.id)}
            inquiryForm={
              activeSlotId === slot.id ? renderInquiryForm(slot) : null
            }
            actions={
              <SponsorSaveButton
                itemType="sponsorship_slot"
                itemId={slot.id}
              />
            }
          />
        ))}
      </div>

      {remaining > 0 ? (
        <div className="flex justify-center pt-2">
          <Button variant="secondary" onClick={onShowMore}>
            Show more ({Math.min(remaining, SPONSOR_SLOTS_PAGE_SIZE)} of{" "}
            {remaining})
          </Button>
        </div>
      ) : null}
    </div>
  );
}
