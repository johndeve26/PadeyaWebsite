"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { StartMessageButton } from "@/components/messaging/StartMessageButton";
import { MerchActionsMenu } from "@/components/merch/buyer/MerchActionsMenu";
import { MerchOrderTimeline } from "@/components/merch/buyer/MerchOrderTimeline";
import { MerchStatusBadge } from "@/components/merch/buyer/MerchStatusBadge";
import { MerchFallbackVisual } from "@/components/merch/MerchFallbackVisual";
import { Button, useToast } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatDate } from "@/lib/format";
import {
  fulfillmentMethodLabel,
  isMerchCancelledLike,
  isMerchCompleted,
  merchPrimaryAction,
  merchStatusPresentation,
  shortenMerchCode,
} from "@/lib/merch/buyer-merch-wallet";
import { readCachedMerchPickup } from "@/lib/pwa/offline-merch-cache";
import type { MerchFulfillment } from "@/lib/types/merch";

export function BuyerMerchPassCard({
  row,
  tone = "active",
  onPickupQr,
}: {
  row: MerchFulfillment;
  tone?: "active" | "completed" | "cancelled";
  onPickupQr: (row: MerchFulfillment) => void;
}) {
  const router = useRouter();
  const { push } = useToast();
  const { workspaces } = useHostWorkspace();
  const [detailsOpen, setDetailsOpen] = useState(false);
  const presentation = merchStatusPresentation(row);
  const primary = merchPrimaryAction(row);
  const inactive = isMerchCancelledLike(row);
  const completed = isMerchCompleted(row);
  const messageId = `msg-merch-${row.order_item_id || row.id}`;
  const offline = Boolean(readCachedMerchPickup(row.order_item_id || row.id));
  const detailHref = `/dashboard/merchandise/${row.order_item_id || row.id}`;
  const showMessageHost = useMemo(
    () =>
      Boolean(
        row.host_id && !workspaces.some((w) => w.host_id === row.host_id),
      ),
    [row.host_id, workspaces],
  );

  function runPrimary() {
    if (primary.kind === "pickup_qr") {
      onPickupQr(row);
      return;
    }
    if (primary.kind === "track") {
      setDetailsOpen(true);
      return;
    }
    router.push(`/dashboard/orders/${row.order_id}`);
  }

  return (
    <article
      className={cn(
        "overflow-hidden rounded-[var(--radius-xl)] border bg-card shadow-[var(--shadow-soft)] dark:bg-surface-elevated",
        tone === "cancelled" && "border-border/70 opacity-90",
        tone === "completed" && "border-border/80",
        tone === "active" && primary.emphasis === "ready" && "border-border",
      )}
    >
      <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-stretch sm:p-5">
        <div className="relative h-36 w-full shrink-0 overflow-hidden rounded-[var(--radius-md)] bg-muted sm:h-auto sm:w-32 sm:min-h-[8.5rem]">
          {row.product_image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={row.product_image_url}
              alt=""
              className="h-full w-full object-cover"
            />
          ) : (
            <MerchFallbackVisual
              productName={row.product_name_snapshot}
              eventTitle={row.event_title}
              compact
            />
          )}
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
            <div className="min-w-0 space-y-1.5">
              <h3
                className={cn(
                  "text-base font-extrabold tracking-tight sm:text-lg",
                  inactive ? "text-muted-foreground" : "text-heading",
                )}
              >
                {row.product_name_snapshot}
              </h3>
              <p className="text-sm text-muted-foreground">
                {row.variant_label_snapshot} · Qty {row.quantity}
              </p>
              <p className="text-sm text-muted-foreground">
                {[row.event_title, row.host_name].filter(Boolean).join(" · ")}
              </p>
              <div className="flex flex-wrap items-center gap-2 pt-0.5">
                <MerchStatusBadge
                  label={presentation.fulfillmentLabel}
                  tone={presentation.fulfillmentTone}
                />
                {presentation.paymentLabel &&
                presentation.paymentLabel !== presentation.fulfillmentLabel ? (
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
            </div>

            <div className="flex shrink-0 flex-col gap-2 sm:items-end">
              <Button
                size={primary.emphasis === "ready" ? "md" : "sm"}
                variant={
                  primary.emphasis === "ready"
                    ? "primary"
                    : primary.emphasis === "inactive"
                      ? "secondary"
                      : "secondary"
                }
                className="min-h-11 w-full sm:min-h-0 sm:w-auto"
                onClick={runPrimary}
              >
                {primary.label}
              </Button>
              <div className="flex flex-wrap items-center gap-2">
                <MerchActionsMenu
                  row={row}
                  onPickupQr={() => onPickupQr(row)}
                  onMessageHost={
                    showMessageHost
                      ? () => document.getElementById(messageId)?.click()
                      : undefined
                  }
                  onCopied={(label) => push({ title: label, tone: "success" })}
                  onError={(message) =>
                    push({ title: message, tone: "danger" })
                  }
                />
                {showMessageHost ? (
                  <StartMessageButton
                    id={messageId}
                    hostId={row.host_id}
                    hostUsername={row.host_slug || undefined}
                    relatedEventId={row.event_id ?? undefined}
                    relatedMerchOrderItemId={row.order_item_id}
                    productName={row.product_name_snapshot}
                    label="Message host"
                    size="sm"
                    variant="ghost"
                    returnPath="/dashboard/merchandise"
                    className="sr-only"
                  />
                ) : null}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {row.order_reference ? (
              <span>Order {shortenMerchCode(row.order_reference)}</span>
            ) : null}
            {row.pickup_code && !inactive ? (
              <span className="font-mono">
                Pickup {shortenMerchCode(row.pickup_code, { head: 7, tail: 4 })}
              </span>
            ) : null}
            {offline && !inactive ? <span>Saved offline</span> : null}
            {completed && (row.fulfilled_at || row.delivered_at) ? (
              <span>
                {formatDate(row.fulfilled_at || row.delivered_at)}
              </span>
            ) : null}
          </div>

          {inactive ? (
            <p className="text-sm font-medium text-muted-foreground">
              {presentation.invalidCopy}
            </p>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setDetailsOpen((v) => !v)}
              aria-expanded={detailsOpen}
            >
              {detailsOpen ? "Hide details" : "Details"}
            </Button>
            {row.event_slug ? (
              <Link href={`/events/${row.event_slug}`}>
                <Button size="sm" variant="ghost">
                  View event
                </Button>
              </Link>
            ) : null}
            {completed ? (
              <Link href={detailHref}>
                <Button size="sm" variant="ghost">
                  Leave review
                </Button>
              </Link>
            ) : null}
            {inactive ? (
              <>
                <Link href={`/dashboard/orders/${row.order_id}`}>
                  <Button size="sm" variant="secondary">
                    View order
                  </Button>
                </Link>
                <Link href="/support">
                  <Button size="sm" variant="ghost">
                    Contact support
                  </Button>
                </Link>
              </>
            ) : null}
          </div>

          {detailsOpen ? (
            <div className="space-y-3 rounded-[var(--radius-md)] border border-border bg-muted/30 px-3 py-3">
              <MerchOrderTimeline row={row} />
              {!inactive &&
              (row.fulfillment_method || "pickup").toLowerCase() !== "pickup" ? (
                <div className="space-y-1 text-sm text-muted-foreground">
                  {row.tracking_number ? (
                    <p>
                      Tracking{" "}
                      <span className="font-semibold text-foreground">
                        {shortenMerchCode(row.tracking_number)}
                      </span>
                      {row.carrier ? ` · ${row.carrier}` : ""}
                    </p>
                  ) : (
                    <p>Tracking appears after the host ships your order.</p>
                  )}
                  {row.shipping_address?.city ? (
                    <p>
                      Ship to area ·{" "}
                      {[
                        row.shipping_address.city,
                        row.shipping_address.state,
                        row.shipping_address.country,
                      ]
                        .filter(Boolean)
                        .join(", ")}
                    </p>
                  ) : null}
                </div>
              ) : null}
              {!inactive &&
              (row.fulfillment_method || "pickup").toLowerCase() === "pickup" ? (
                <div className="space-y-1 text-sm text-muted-foreground">
                  {row.pickup_location_label ? (
                    <p>Location · {row.pickup_location_label}</p>
                  ) : null}
                  {row.pickup_time_window ? (
                    <p>Window · {row.pickup_time_window}</p>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}
