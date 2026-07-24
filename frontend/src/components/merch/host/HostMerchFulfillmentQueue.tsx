"use client";

import { useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { HostMessageBuyerButton } from "@/components/messaging/HostMessageBuyerButton";
import {
  Badge,
  Button,
  EmptyState,
  FilterBar,
  Input,
  Select,
  StatusBadge,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { formatDateTime } from "@/lib/format";
import { fulfillmentMethodLabel } from "@/lib/merch-buyer-status";
import {
  addMerchFulfillmentNote,
  deliverMerchFulfillment,
  fulfillMerch,
  shipMerchFulfillment,
  updateMerchFulfillmentStatus,
} from "@/lib/merch-api";
import type { MerchFulfillment } from "@/lib/types/merch";

const FILTERS = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending pickup" },
  { value: "ready", label: "Ready" },
  { value: "shipping", label: "To ship / in transit" },
  { value: "picked_up", label: "Picked up / delivered" },
  { value: "cancelled", label: "Cancelled / refunded" },
] as const;

function matchesFilter(row: MerchFulfillment, filter: string): boolean {
  if (filter === "all") return true;
  if (filter === "pending") return row.status === "awaiting_pickup";
  if (filter === "ready") return row.status === "collect_at_stand";
  if (filter === "shipping") {
    return (
      row.status === "awaiting_shipment" ||
      row.status === "packed" ||
      row.status === "shipped"
    );
  }
  if (filter === "picked_up") {
    return row.status === "fulfilled" || row.status === "delivered";
  }
  if (filter === "cancelled") return row.status === "cancelled";
  return true;
}

function canConfirmPickup(row: MerchFulfillment): boolean {
  return row.status === "awaiting_pickup" || row.status === "collect_at_stand";
}

function isShippingLine(row: MerchFulfillment): boolean {
  return (row.fulfillment_method || "pickup").toLowerCase() === "shipping";
}

function statusLabel(row: MerchFulfillment): string | undefined {
  if (row.status === "fulfilled") return "Picked up";
  if (row.status === "collect_at_stand") return "Ready for pickup";
  if (row.status === "awaiting_pickup") return "Confirmed";
  if (row.status === "awaiting_shipment") return "Awaiting shipment";
  if (row.status === "packed") return "Packed";
  if (row.status === "shipped") return "Shipped";
  if (row.status === "delivered") return "Delivered";
  if (row.status === "cancelled") return "Cancelled / refunded";
  return undefined;
}

function statusTone(row: MerchFulfillment): string {
  if (row.status === "fulfilled" || row.status === "delivered") return "picked_up";
  if (row.status === "collect_at_stand") return "ready_for_pickup";
  if (row.status === "awaiting_pickup") return "confirmed";
  if (row.status === "shipped") return "shipped";
  if (row.status === "awaiting_shipment" || row.status === "packed") {
    return "awaiting_shipment";
  }
  return row.status;
}

export function HostMerchFulfillmentQueue({
  rows,
  onChanged,
  emptyTitle = "No merch fulfillments yet",
  emptyDescription = "Paid merch lines show here for pickup desk or shipping.",
  showFilters = true,
}: {
  rows: MerchFulfillment[];
  onChanged: () => void | Promise<void>;
  emptyTitle?: string;
  emptyDescription?: string;
  showFilters?: boolean;
}) {
  const toast = useToast();
  const { user } = useAuth();
  const canFulfill = userHasPermission(user, "merch.fulfill", "merch.manage_own");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<string>("all");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [tracking, setTracking] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const filtered = rows.filter((row) => {
      if (!matchesFilter(row, filter)) return false;
      if (!needle) return true;
      const haystack = [
        row.pickup_code,
        row.buyer_name,
        row.order_reference,
        row.product_name_snapshot,
        row.variant_label_snapshot,
        row.tracking_number,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    });
    if (!needle) return filtered;
    return [...filtered].sort((a, b) => {
      const aExact = a.pickup_code.toLowerCase() === needle ? 0 : 1;
      const bExact = b.pickup_code.toLowerCase() === needle ? 0 : 1;
      return aExact - bExact;
    });
  }, [rows, search, filter]);

  const exactMatch = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return null;
    return (
      rows.find((row) => row.pickup_code.toLowerCase() === needle) ?? null
    );
  }, [rows, search]);

  async function onFulfill(id: string) {
    setBusyId(id);
    try {
      await fulfillMerch(id);
      toast.push({ tone: "success", title: "Pickup confirmed" });
      await onChanged();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: err instanceof ApiError ? err.detail : "Fulfill failed",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onReady(id: string) {
    setBusyId(id);
    try {
      await updateMerchFulfillmentStatus(id, "collect_at_stand");
      toast.push({ tone: "success", title: "Marked ready for pickup" });
      await onChanged();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: err instanceof ApiError ? err.detail : "Update failed",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onShip(id: string) {
    setBusyId(id);
    try {
      await shipMerchFulfillment(id, {
        tracking_number: tracking[id]?.trim() || undefined,
      });
      toast.push({ tone: "success", title: "Marked shipped" });
      await onChanged();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: err instanceof ApiError ? err.detail : "Ship failed",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onDeliver(id: string) {
    setBusyId(id);
    try {
      await deliverMerchFulfillment(id);
      toast.push({ tone: "success", title: "Marked delivered" });
      await onChanged();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: err instanceof ApiError ? err.detail : "Deliver failed",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onNote(id: string) {
    const note = notes[id]?.trim() ?? "";
    if (note.length < 2) {
      toast.push({ tone: "danger", title: "Add a short note first" });
      return;
    }
    setBusyId(id);
    try {
      await addMerchFulfillmentNote(id, note);
      setNotes((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      toast.push({ tone: "success", title: "Note added" });
      await onChanged();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: err instanceof ApiError ? err.detail : "Could not add note",
      });
    } finally {
      setBusyId(null);
    }
  }

  function renderRow(row: MerchFulfillment, highlighted = false) {
    const busy = busyId === row.id;
    const shipping = isShippingLine(row);
    const open = !shipping && canConfirmPickup(row);
    const canShip =
      shipping &&
      (row.status === "awaiting_shipment" || row.status === "packed");
    const canDeliver = shipping && row.status === "shipped";
    const pickedUp = row.status === "fulfilled" || row.status === "delivered";
    const blocked = row.status === "cancelled";
    const pickupBits = [
      row.pickup_location_label,
      row.pickup_time_window,
      row.pickup_instructions_snapshot,
    ].filter(Boolean);
    const addr = shipping ? row.shipping_address : null;

    return (
      <li
        key={row.id}
        className={
          highlighted
            ? "space-y-3 rounded-[var(--radius-md)] border border-foreground/30 bg-muted/40 p-4"
            : "space-y-3 border-b border-border pb-4 last:border-0 last:pb-0"
        }
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              {!shipping ? (
                <Badge tone="dark" size="sm">
                  {row.pickup_code || "—"}
                </Badge>
              ) : null}
              <Badge tone="outline" size="sm">
                {fulfillmentMethodLabel(row.fulfillment_method)}
              </Badge>
              <StatusBadge
                status={statusTone(row)}
                label={statusLabel(row)}
              />
              {row.has_ticket ? (
                <Badge tone="outline" size="sm">
                  Has ticket
                </Badge>
              ) : (
                <Badge tone="outline" size="sm">
                  Merch only
                </Badge>
              )}
            </div>
            <div>
              <p className="font-extrabold tracking-tight text-foreground">
                {row.product_name_snapshot}
              </p>
              <p className="text-sm text-muted-foreground">
                {row.variant_label_snapshot} · Qty {row.quantity}
              </p>
            </div>
            <div className="space-y-0.5 text-sm text-muted-foreground">
              {row.buyer_name ? <p>Buyer: {row.buyer_name}</p> : null}
              {row.order_reference ? (
                <p>Order: {row.order_reference}</p>
              ) : null}
              <p>{row.event_title ?? "Event"}</p>
            </div>
            {!shipping && pickupBits.length > 0 ? (
              <div className="text-xs text-muted-foreground">
                <p className="font-semibold text-foreground">Pickup</p>
                {pickupBits.map((line) => (
                  <p key={line}>{line}</p>
                ))}
              </div>
            ) : null}
            {shipping && addr ? (
              <div className="space-y-0.5 text-xs text-muted-foreground">
                <p className="font-semibold text-foreground">Ship to</p>
                {addr.recipient_name ? <p>{addr.recipient_name}</p> : null}
                {addr.phone ? <p>{addr.phone}</p> : null}
                {addr.line1 ? <p>{addr.line1}</p> : null}
                {addr.line2 ? <p>{addr.line2}</p> : null}
                <p>
                  {[addr.city, addr.state, addr.postal_code, addr.country]
                    .filter(Boolean)
                    .join(", ")}
                </p>
                {addr.notes ? <p>Notes: {addr.notes}</p> : null}
                {!addr.line1 && !canFulfill ? (
                  <p className="italic">
                    City/region only — fulfill permission required for full
                    address.
                  </p>
                ) : null}
              </div>
            ) : null}
            {shipping && row.tracking_number ? (
              <p className="text-xs text-muted-foreground">
                Tracking{" "}
                <span className="font-semibold text-foreground">
                  {row.tracking_number}
                </span>
                {row.carrier ? ` · ${row.carrier}` : ""}
              </p>
            ) : null}
            {row.fulfillment_notes ? (
              <p className="text-xs text-muted-foreground">
                <span className="font-semibold text-foreground">Desk note: </span>
                {row.fulfillment_notes}
              </p>
            ) : null}
            {pickedUp ? (
              <p className="text-xs font-semibold text-foreground">
                {row.status === "delivered" ? "Delivered" : "Collected"}
                {row.fulfilled_at || row.delivered_at
                  ? ` ${formatDateTime(row.delivered_at || row.fulfilled_at)}`
                  : ""}
                {row.fulfilled_by_name ? ` · ${row.fulfilled_by_name}` : ""}
              </p>
            ) : null}
            {blocked ? (
              <p className="text-xs font-semibold text-danger">
                Cannot fulfill — cancelled or refunded
              </p>
            ) : null}
          </div>
          <div className="flex shrink-0 flex-wrap gap-1.5">
            {row.buyer_user_id ? (
              <HostMessageBuyerButton
                fanUserId={row.buyer_user_id}
                relatedEventId={row.event_id ?? undefined}
                relatedMerchOrderItemId={row.order_item_id}
                productName={row.product_name_snapshot}
              />
            ) : null}
            {open && canFulfill ? (
              <>
                {row.status === "awaiting_pickup" ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void onReady(row.id)}
                  >
                    Ready at stand
                  </Button>
                ) : null}
                <Button
                  size="sm"
                  disabled={busy}
                  onClick={() => void onFulfill(row.id)}
                >
                  Confirm pickup
                </Button>
              </>
            ) : null}
            {canShip && canFulfill ? (
              <Button
                size="sm"
                disabled={busy}
                onClick={() => void onShip(row.id)}
              >
                Mark shipped
              </Button>
            ) : null}
            {canDeliver && canFulfill ? (
              <Button
                size="sm"
                disabled={busy}
                onClick={() => void onDeliver(row.id)}
              >
                Mark delivered
              </Button>
            ) : null}
          </div>
        </div>
        {canShip && canFulfill ? (
          <Input
            label="Tracking / reference"
            value={tracking[row.id] ?? ""}
            onChange={(e) =>
              setTracking((prev) => ({ ...prev, [row.id]: e.target.value }))
            }
            placeholder="Optional carrier tracking number"
          />
        ) : null}
        {canFulfill ? (
          <div className="grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
            <Textarea
              label="Desk note"
              rows={2}
              value={notes[row.id] ?? ""}
              onChange={(e) =>
                setNotes((prev) => ({ ...prev, [row.id]: e.target.value }))
              }
              placeholder="Optional note (audited)"
            />
            <Button
              size="sm"
              variant="secondary"
              disabled={busy}
              onClick={() => void onNote(row.id)}
            >
              Add note
            </Button>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            View only — fulfill actions require merch fulfill permission.
          </p>
        )}
      </li>
    );
  }

  return (
    <div className="space-y-4">
      {showFilters ? (
        <FilterBar
          trailing={
            <span className="text-sm text-muted-foreground">
              {visible.length} of {rows.length}
            </span>
          }
        >
          <Input
            label="Lookup code / tracking"
            placeholder="MRCH-… or tracking"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
          <Select
            label="Status"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            {FILTERS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </Select>
        </FilterBar>
      ) : null}

      <p className="text-xs text-muted-foreground">
        Pickup codes are separate from ticket QR. Shipping addresses stay private
        — only staff with fulfill permission see full ship-to details.
      </p>

      {exactMatch ? (
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
            Exact code match
          </p>
          <ul>{renderRow(exactMatch, true)}</ul>
        </div>
      ) : null}

      {visible.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      ) : (
        <ul className="space-y-4">
          {visible
            .filter((row) => !exactMatch || row.id !== exactMatch.id)
            .map((row) => renderRow(row))}
        </ul>
      )}
    </div>
  );
}
