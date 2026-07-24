"use client";

import { EventMerchDetail } from "@/components/merch/EventMerchDetail";
import { Modal } from "@/components/ui";
import type { MerchCatalogProduct } from "@/lib/types/merch";

type Props = {
  open: boolean;
  onClose: () => void;
  product: MerchCatalogProduct | null;
  eventId: string;
  eventSlug: string;
  eventTitle: string;
  hostId?: string | null;
  hostName?: string | null;
  hostSlug?: string | null;
  referralCode?: string;
  onAdded?: () => void;
};

export function EventMerchDetailModal({
  open,
  onClose,
  product,
  eventId,
  eventSlug,
  eventTitle,
  hostId,
  hostName,
  hostSlug,
  referralCode,
  onAdded,
}: Props) {
  if (!product) return null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={product.name}
      description={
        product.short_description ||
        "Pre-order official merch and pick it up at the event."
      }
      className="sm:max-w-xl"
    >
      <EventMerchDetail
        product={product}
        eventId={eventId}
        eventSlug={eventSlug}
        eventTitle={eventTitle}
        hostId={hostId}
        hostName={hostName}
        hostSlug={hostSlug}
        referralCode={referralCode}
        stickyPurchaseBar={false}
        onAdded={() => {
          onAdded?.();
          onClose();
        }}
      />
    </Modal>
  );
}
