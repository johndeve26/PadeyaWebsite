"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { MerchPickupQr } from "@/components/merch/MerchPickupQr";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { Alert, Button, SkeletonLoader, StatusBadge } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { ownedHostIds } from "@/lib/host-affiliation";
import {
  createMerchReview,
  fetchMyMerchItem,
  fetchMyMerchReviewForOrderItem,
  removeMerchReview,
  updateMerchReview,
  type MerchReviewPublic,
} from "@/lib/merch-api";
import {
  buyerMerchStatusLabel,
  resolveBuyerMerchDisplayStatus,
} from "@/lib/merch-buyer-status";
import {
  cacheMerchPickupForOffline,
  cachedMerchAsFulfillment,
  readCachedMerchPickup,
} from "@/lib/pwa/offline-merch-cache";
import { useOnlineStatus } from "@/lib/pwa/use-online-status";
import type { MerchFulfillment } from "@/lib/types/merch";

export default function BuyerMerchDetailPage() {
  const params = useParams<{ orderItemId: string }>();
  const online = useOnlineStatus();
  const { workspaces } = useHostWorkspace();
  const [row, setRow] = useState<MerchFulfillment | null>(() => {
    const cached = readCachedMerchPickup(params.orderItemId);
    return cached ? cachedMerchAsFulfillment(cached) : null;
  });
  const [fromCache, setFromCache] = useState(
    () => Boolean(readCachedMerchPickup(params.orderItemId)),
  );
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [rating, setRating] = useState(5);
  const [reviewBody, setReviewBody] = useState("");
  const [reviewNote, setReviewNote] = useState<string | null>(null);
  const [myReview, setMyReview] = useState<MerchReviewPublic | null>(null);
  const [reviewBusy, setReviewBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      const cached = readCachedMerchPickup(params.orderItemId);
      try {
        const item = await fetchMyMerchItem(params.orderItemId);
        if (!active) return;
        cacheMerchPickupForOffline(item);
        setRow(item);
        setFromCache(false);
        setError(null);
        setNote(null);
        if (item.order_status === "paid") {
          const existing = await fetchMyMerchReviewForOrderItem(
            item.order_item_id,
          ).catch(() => null);
          if (!active) return;
          setMyReview(existing);
          if (existing) {
            setRating(existing.rating);
            setReviewBody(existing.body || "");
          }
        }
      } catch (err) {
        if (!active) return;
        if (cached) {
          setRow(cachedMerchAsFulfillment(cached));
          setFromCache(true);
          setNote(
            "Showing cached merch pickup QR — desk still validates online. Shipping details are never stored offline.",
          );
          setError(null);
        } else {
          setError(err instanceof ApiError ? err.detail : "Merch not found");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.orderItemId]);

  const displayStatus = row
    ? resolveBuyerMerchDisplayStatus({
        displayStatus: row.display_status,
        fulfillmentStatus: row.status,
        orderStatus: row.order_status,
      })
    : null;

  const qrDisabled =
    !displayStatus ||
    displayStatus === "pending_payment" ||
    displayStatus === "picked_up" ||
    displayStatus === "cancelled" ||
    displayStatus === "refunded";

  const affiliatedWithProductHost = Boolean(
    row?.host_id &&
      ownedHostIds(workspaces).includes(row.host_id),
  );
  const showReviewForm =
    row?.order_status === "paid" &&
    !fromCache &&
    (Boolean(myReview) || !affiliatedWithProductHost);

  async function onSubmitReview(e: React.FormEvent) {
    e.preventDefault();
    if (!row) return;
    setReviewBusy(true);
    setReviewNote(null);
    try {
      if (myReview) {
        const updated = await updateMerchReview(myReview.id, {
          rating,
          body: reviewBody || null,
        });
        setMyReview(updated);
        setReviewNote("Review updated.");
      } else {
        const created = await createMerchReview(row.order_item_id, {
          rating,
          body: reviewBody || undefined,
        });
        setMyReview(created);
        setReviewNote("Review submitted — verified purchase.");
      }
    } catch (err) {
      setReviewNote(
        err instanceof ApiError ? err.detail : "Could not save review",
      );
    } finally {
      setReviewBusy(false);
    }
  }

  async function onRemoveReview() {
    if (!myReview) return;
    setReviewBusy(true);
    setReviewNote(null);
    try {
      await removeMerchReview(myReview.id);
      setMyReview(null);
      setRating(5);
      setReviewBody("");
      setReviewNote("Review removed.");
    } catch (err) {
      setReviewNote(
        err instanceof ApiError ? err.detail : "Could not remove review",
      );
    } finally {
      setReviewBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Merchandise"
      title={row?.product_name_snapshot || "Merch item"}
      description="Pickup details after verified payment on Pàdéyá."
      actions={
        <Link href="/dashboard/merchandise">
          <Button variant="secondary" size="sm">
            All merch
          </Button>
        </Link>
      }
    >
      {!online || fromCache ? (
        <Alert tone="warning" title={fromCache ? "Offline cache" : "Offline"}>
          {note ||
            "You’re offline — cached merch pickup QR may still display. Desk validation needs a connection."}
        </Alert>
      ) : null}
      {error ? (
        <Alert tone="danger" title="Unavailable">
          {error}
        </Alert>
      ) : null}
      {!row && !error ? <SkeletonLoader lines={5} /> : null}
      {row && displayStatus ? (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-2">
            <StatusBadge
              status={displayStatus}
              label={buyerMerchStatusLabel(displayStatus)}
            />
            {row.fulfillment_method ? (
              <StatusBadge
                status={row.fulfillment_method}
                label={row.fulfillment_method.replace(/_/g, " ")}
              />
            ) : null}
          </div>
          <p className="text-sm text-muted-foreground">
            {row.variant_label_snapshot} · Qty {row.quantity}
            {row.event_title ? ` · ${row.event_title}` : ""}
          </p>

          {(row.fulfillment_method || "pickup") === "pickup" ? (
            <MerchPickupQr
              pickupCode={row.pickup_code}
              qrToken={qrDisabled ? null : row.qr_token}
              qrTyp={row.qr_typ}
              disabled={qrDisabled}
              offlineHint={
                fromCache && !qrDisabled
                  ? "Cached for offline display — never includes shipping address."
                  : null
              }
            />
          ) : (
            <p className="text-sm text-muted-foreground">
              Fulfillment: {row.fulfillment_method}
              {row.tracking_number
                ? ` · Tracking ${row.tracking_number}`
                : ""}
            </p>
          )}

          {showReviewForm ? (
            <form
              className="space-y-3 border-t border-border pt-4"
              onSubmit={(e) => void onSubmitReview(e)}
            >
              <p className="text-sm font-semibold">
                {myReview ? "Your review" : "Leave a review"}
              </p>
              {myReview ? (
                <p className="text-xs text-muted-foreground">
                  Verified purchase · you can edit or remove this review.
                </p>
              ) : null}
              <label className="block text-xs text-muted-foreground">
                Rating
                <select
                  className="mt-1 block w-full border border-border bg-background px-2 py-2 text-sm"
                  value={rating}
                  onChange={(e) => setRating(Number(e.target.value))}
                >
                  {[5, 4, 3, 2, 1].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
              <textarea
                className="w-full border border-border bg-background px-3 py-2 text-sm"
                rows={3}
                placeholder="Optional comments"
                value={reviewBody}
                onChange={(e) => setReviewBody(e.target.value)}
              />
              <div className="flex flex-wrap gap-2">
                <Button type="submit" size="sm" disabled={reviewBusy}>
                  {myReview ? "Save changes" : "Submit review"}
                </Button>
                {myReview ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={reviewBusy}
                    onClick={() => void onRemoveReview()}
                  >
                    Remove review
                  </Button>
                ) : null}
              </div>
              {reviewNote ? (
                <p className="text-xs text-muted-foreground">{reviewNote}</p>
              ) : null}
              {myReview?.host_reply ? (
                <p className="text-sm text-foreground">
                  Host reply: {myReview.host_reply}
                </p>
              ) : null}
            </form>
          ) : null}
        </div>
      ) : null}
    </DashboardShell>
  );
}
