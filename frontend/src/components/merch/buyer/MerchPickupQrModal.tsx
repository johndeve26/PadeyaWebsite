"use client";

import { useEffect, useState } from "react";

import { StartMessageButton } from "@/components/messaging/StartMessageButton";
import { MerchPickupQr } from "@/components/merch/MerchPickupQr";
import { MerchStatusBadge } from "@/components/merch/buyer/MerchStatusBadge";
import {
  Alert,
  Button,
  Modal,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { fetchMyMerchItem } from "@/lib/merch-api";
import {
  fulfillmentMethodLabel,
  merchStatusPresentation,
} from "@/lib/merch/buyer-merch-wallet";
import {
  cacheMerchPickupForOffline,
  cachedMerchAsFulfillment,
  readCachedMerchPickup,
} from "@/lib/pwa/offline-merch-cache";
import type { MerchFulfillment } from "@/lib/types/merch";

export function MerchPickupQrModal({
  orderItemId,
  seed,
  open,
  onClose,
}: {
  orderItemId: string;
  seed?: MerchFulfillment | null;
  open: boolean;
  onClose: () => void;
}) {
  const { push } = useToast();
  const [row, setRow] = useState<MerchFulfillment | null>(() => {
    if (seed && (seed.order_item_id === orderItemId || seed.id === orderItemId)) {
      return seed;
    }
    const cached = readCachedMerchPickup(orderItemId);
    return cached ? cachedMerchAsFulfillment(cached) : null;
  });
  const [loading, setLoading] = useState(!row);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const item = await fetchMyMerchItem(orderItemId);
        if (cancelled) return;
        cacheMerchPickupForOffline(item);
        setRow(item);
        setError(null);
      } catch {
        if (cancelled) return;
        const cached = readCachedMerchPickup(orderItemId);
        if (cached) {
          setRow(cachedMerchAsFulfillment(cached));
          setError(null);
        } else if (!seed) {
          setError("Could not load pickup pass");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [orderItemId, seed]);

  const presentation = row ? merchStatusPresentation(row) : null;
  const pickedUp = presentation?.fulfillmentLabel === "Picked up";
  const invalid = Boolean(presentation?.invalidCopy);

  async function onCopy() {
    if (!row?.pickup_code) return;
    try {
      await navigator.clipboard.writeText(row.pickup_code);
      push({ title: "Pickup code copied", tone: "success" });
    } catch {
      push({ title: "Could not copy code", tone: "danger" });
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={row?.product_name_snapshot || "Pickup pass"}
      description={
        invalid
          ? presentation?.invalidCopy ?? undefined
          : pickedUp
            ? "This item has already been picked up."
            : "Show this QR code at the merch stand."
      }
      className="sm:max-w-md"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Done
          </Button>
          <Button
            variant="secondary"
            onClick={() => void onCopy()}
            disabled={!row?.pickup_code || invalid}
          >
            Copy pickup code
          </Button>
          {row?.host_id ? (
            <StartMessageButton
              hostId={row.host_id}
              hostUsername={row.host_slug || undefined}
              relatedEventId={row.event_id ?? undefined}
              relatedMerchOrderItemId={row.order_item_id}
              productName={row.product_name_snapshot}
              label="Message host"
              size="sm"
              variant="secondary"
              returnPath="/dashboard/merchandise"
            />
          ) : null}
        </>
      }
    >
      {error ? (
        <Alert tone="danger" title="Pickup unavailable">
          {error}
        </Alert>
      ) : null}

      {loading && !row ? <SkeletonLoader lines={4} /> : null}

      {row && presentation ? (
        <div className="space-y-5">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <MerchStatusBadge
                label={presentation.fulfillmentLabel}
                tone={presentation.fulfillmentTone}
              />
              {presentation.paymentLabel ? (
                <MerchStatusBadge
                  label={presentation.paymentLabel}
                  tone={presentation.paymentTone ?? "neutral"}
                />
              ) : null}
              <MerchStatusBadge
                label={fulfillmentMethodLabel(row.fulfillment_method)}
                tone="outline"
              />
            </div>
            <p className="text-sm text-muted-foreground">
              {[row.event_title, row.host_name].filter(Boolean).join(" · ")}
            </p>
            <p className="text-sm text-muted-foreground">
              {row.variant_label_snapshot} · Qty {row.quantity}
            </p>
          </div>

          {(row.pickup_location_label ||
            row.pickup_time_window ||
            row.pickup_instructions_snapshot) &&
          !invalid ? (
            <div className="space-y-1 rounded-[var(--radius-md)] border border-border bg-muted/40 px-3 py-3 text-sm text-muted-foreground">
              {row.pickup_location_label ? (
                <p>
                  <span className="font-semibold text-foreground">Location · </span>
                  {row.pickup_location_label}
                </p>
              ) : null}
              {row.pickup_time_window ? (
                <p>
                  <span className="font-semibold text-foreground">Window · </span>
                  {row.pickup_time_window}
                </p>
              ) : null}
              {row.pickup_instructions_snapshot ? (
                <p>{row.pickup_instructions_snapshot}</p>
              ) : null}
            </div>
          ) : null}

          <div className="flex flex-col items-center gap-3 rounded-[var(--radius-lg)] border border-border bg-muted/30 px-4 py-5">
            {invalid || pickedUp ? (
              <div className="flex min-h-[180px] w-full max-w-[280px] flex-col items-center justify-center gap-3 rounded-[var(--radius-xl)] bg-paper px-4 text-center ring-1 ring-border">
                <p className="text-sm font-semibold text-ink/70">
                  {invalid
                    ? "No longer valid for pickup"
                    : "Picked up — QR no longer active"}
                </p>
                {row.pickup_code ? (
                  <p className="font-mono text-sm font-bold text-ink/80">
                    {row.pickup_code}
                  </p>
                ) : null}
              </div>
            ) : (
              <div className="flex w-full flex-col items-center">
                <MerchPickupQr
                  pickupCode={row.pickup_code}
                  qrToken={row.qr_token}
                  qrTyp={row.qr_typ}
                  disabled={!presentation.showPickupQr}
                />
              </div>
            )}
          </div>
        </div>
      ) : null}
    </Modal>
  );
}
