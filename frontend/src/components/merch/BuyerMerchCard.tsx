"use client";

import Link from "next/link";

import { StartMessageButton } from "@/components/messaging/StartMessageButton";
import { Badge, Button, Card, StatusBadge } from "@/components/ui";
import {
  buyerMerchStatusLabel,
  fulfillmentMethodLabel,
  resolveBuyerMerchDisplayStatus,
} from "@/lib/merch-buyer-status";
import type { MerchFulfillment } from "@/lib/types/merch";

type Props = {
  row: MerchFulfillment;
};

function shippingHint(row: MerchFulfillment): string | null {
  const addr = row.shipping_address;
  if (!addr) return null;
  const parts = [addr.city, addr.state, addr.country].filter(Boolean);
  return parts.length ? parts.join(", ") : null;
}

export function BuyerMerchCard({ row }: Props) {
  const displayStatus = resolveBuyerMerchDisplayStatus({
    displayStatus: row.display_status,
    fulfillmentStatus: row.status,
    orderStatus: row.order_status,
  });
  const statusLabel = buyerMerchStatusLabel(displayStatus);
  const pending = displayStatus === "pending_payment";
  const method = (row.fulfillment_method || "pickup").toLowerCase();
  const isPickup = method === "pickup";
  const pickupBits = [
    row.pickup_location_label,
    row.pickup_time_window,
    row.pickup_instructions_snapshot,
  ].filter(Boolean);
  const shipHint = shippingHint(row);

  return (
    <Card padded={false} className="overflow-hidden">
      <div className="flex flex-col sm:flex-row">
        <div className="relative aspect-[4/3] w-full shrink-0 bg-surface-muted sm:aspect-auto sm:w-36 sm:min-h-[9rem]">
          {row.product_image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={row.product_image_url}
              alt=""
              className="h-full w-full object-cover"
            />
          ) : (
            <span className="flex h-full min-h-[9rem] items-center justify-center text-sm font-bold text-muted-foreground">
              Merch
            </span>
          )}
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-3 p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0 space-y-1">
              <h3 className="text-base font-extrabold tracking-tight text-foreground">
                {row.product_name_snapshot}
              </h3>
              <p className="text-sm text-muted-foreground">
                {row.variant_label_snapshot} · Qty {row.quantity}
              </p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <StatusBadge status={displayStatus} label={statusLabel} />
              <Badge tone="outline" size="sm">
                {fulfillmentMethodLabel(row.fulfillment_method)}
              </Badge>
              {row.order_status ? (
                <StatusBadge
                  status={row.order_status}
                  label={`Order: ${row.order_status.replace(/_/g, " ")}`}
                />
              ) : null}
            </div>
          </div>

          <div className="space-y-1 text-sm text-muted-foreground">
            {row.event_title ? (
              <p>
                Event:{" "}
                <span className="font-semibold text-foreground">
                  {row.event_title}
                </span>
              </p>
            ) : null}
            {row.host_name ? (
              <p>
                Host:{" "}
                {row.host_slug ? (
                  <Link
                    href={`/@${row.host_slug}`}
                    className="font-semibold text-foreground underline-offset-2 hover:underline"
                  >
                    {row.host_name}
                  </Link>
                ) : (
                  <span className="font-semibold text-foreground">
                    {row.host_name}
                  </span>
                )}
              </p>
            ) : null}
            {row.order_reference ? (
              <p className="text-xs">Order {row.order_reference}</p>
            ) : null}
          </div>

          {!pending && isPickup && row.pickup_code ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                Pickup code
              </span>
              <Badge tone="dark" size="sm">
                {row.pickup_code}
              </Badge>
            </div>
          ) : null}

          {isPickup && pickupBits.length > 0 ? (
            <div className="space-y-0.5 text-sm text-muted-foreground">
              <p className="font-semibold text-foreground">Pickup</p>
              {pickupBits.map((line) => (
                <p key={line}>{line}</p>
              ))}
            </div>
          ) : null}

          {!isPickup ? (
            <div className="space-y-0.5 text-sm text-muted-foreground">
              <p className="font-semibold text-foreground">Delivery</p>
              {shipHint ? <p>{shipHint}</p> : null}
              {row.tracking_number ? (
                <p>
                  Tracking{" "}
                  <span className="font-semibold text-foreground">
                    {row.tracking_number}
                  </span>
                  {row.carrier ? ` · ${row.carrier}` : ""}
                </p>
              ) : (
                <p className="text-xs">
                  Tracking appears after the host marks your order shipped.
                </p>
              )}
            </div>
          ) : null}

          <div className="mt-auto flex flex-wrap gap-2 pt-1">
            <Link href={`/dashboard/merchandise/${row.order_item_id || row.id}`}>
              <Button size="sm">
                {pending
                  ? "View status"
                  : isPickup
                    ? "Pickup / QR"
                    : "Delivery status"}
              </Button>
            </Link>
            {row.event_slug ? (
              <Link href={`/events/${row.event_slug}`}>
                <Button size="sm" variant="secondary">
                  View event
                </Button>
              </Link>
            ) : null}
            <Link href={`/dashboard/orders/${row.order_id}`}>
              <Button size="sm" variant="ghost">
                {pending ? "Complete payment" : "View order"}
              </Button>
            </Link>
            {row.host_id ? (
              <StartMessageButton
                hostId={row.host_id}
                hostUsername={row.host_slug || undefined}
                relatedEventId={row.event_id ?? undefined}
                relatedMerchOrderItemId={row.order_item_id}
                productName={row.product_name_snapshot}
                label="Message host"
                size="sm"
                variant="ghost"
                returnPath="/dashboard/merchandise"
              />
            ) : null}
          </div>
        </div>
      </div>
    </Card>
  );
}
