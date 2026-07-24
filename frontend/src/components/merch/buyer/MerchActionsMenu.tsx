"use client";

import { useRouter } from "next/navigation";

import { Dropdown } from "@/components/ui";
import {
  isMerchCancelledLike,
  isMerchReadyPickup,
  merchPrimaryAction,
  merchStatusPresentation,
  shortenMerchCode,
} from "@/lib/merch/buyer-merch-wallet";
import type { MerchFulfillment } from "@/lib/types/merch";

async function copyText(value: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    return false;
  }
}

export function MerchActionsMenu({
  row,
  onPickupQr,
  onMessageHost,
  onCopied,
  onError,
}: {
  row: MerchFulfillment;
  onPickupQr?: () => void;
  onMessageHost?: () => void;
  onCopied?: (label: string) => void;
  onError?: (message: string) => void;
}) {
  const router = useRouter();
  const presentation = merchStatusPresentation(row);
  const primary = merchPrimaryAction(row);
  const inactive = isMerchCancelledLike(row);
  const detailHref = `/dashboard/merchandise/${row.order_item_id || row.id}`;

  const items = [
    ...(primary.kind === "pickup_qr" || isMerchReadyPickup(row)
      ? [
          {
            id: "qr",
            label: "View pickup QR",
            disabled: !presentation.showPickupQr && inactive,
            onSelect: () => onPickupQr?.(),
          },
        ]
      : []),
    {
      id: "event",
      label: "View event",
      disabled: !row.event_slug,
      onSelect: () => {
        if (row.event_slug) router.push(`/events/${row.event_slug}`);
      },
    },
    {
      id: "order",
      label: "View order",
      onSelect: () => router.push(`/dashboard/orders/${row.order_id}`),
    },
    ...(onMessageHost
      ? [
          {
            id: "message",
            label: "Message host",
            disabled: !row.host_id,
            onSelect: () => onMessageHost(),
          },
        ]
      : []),
    {
      id: "copy",
      label: "Copy pickup code",
      disabled: !row.pickup_code || inactive || !presentation.showPickupQr,
      onSelect: () => {
        void (async () => {
          const ok = await copyText(row.pickup_code);
          if (ok) {
            onCopied?.(`Copied ${shortenMerchCode(row.pickup_code)}`);
          } else {
            onError?.("Could not copy pickup code");
          }
        })();
      },
    },
    {
      id: "details",
      label: "View details",
      onSelect: () => router.push(detailHref),
    },
    {
      id: "support",
      label: inactive ? "Contact support" : "Report issue",
      onSelect: () => router.push("/support"),
    },
  ];

  return <Dropdown label="More" align="right" items={items} />;
}
