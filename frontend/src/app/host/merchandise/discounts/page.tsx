"use client";

import { useEffect, useState, type FormEvent } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  SectionHeader,
  Select,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMyEvents } from "@/lib/events-api";
import { formatDate, formatNgn } from "@/lib/format";
import {
  archiveHostMerchDiscount,
  createHostMerchDiscount,
  fetchHostMerchDiscounts,
  updateHostMerchDiscount,
} from "@/lib/merch-api";
import type { EventItem } from "@/lib/types/events";
import type { MerchDiscountCode } from "@/lib/types/merch";

function discountLabel(row: MerchDiscountCode) {
  const value = Number(row.discount_value);
  if (row.discount_type === "percent") return `${value}% off`;
  if (row.discount_type === "free_shipping") return "Free shipping";
  return `${formatNgn(value)} off`;
}

export default function HostMerchDiscountsPage() {
  const [rows, setRows] = useState<MerchDiscountCode[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [discountType, setDiscountType] = useState("percent");
  const [discountValue, setDiscountValue] = useState("10");
  const [appliesTo, setAppliesTo] = useState("merch_only");
  const [eventId, setEventId] = useState("");
  const [minOrder, setMinOrder] = useState("");
  const [usageLimit, setUsageLimit] = useState("");
  const [perBuyerLimit, setPerBuyerLimit] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [productIdsRaw, setProductIdsRaw] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [discountRows, eventRows] = await Promise.all([
      fetchHostMerchDiscounts(),
      fetchMyEvents(),
    ]);
    setRows(discountRows);
    setEvents(eventRows);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load discounts",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const productIds =
        appliesTo === "specific_products"
          ? productIdsRaw
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          : null;
      await createHostMerchDiscount({
        code,
        description: description.trim() || null,
        discount_type: discountType,
        discount_value: Number(discountValue || 0),
        currency: "NGN",
        applies_to: appliesTo,
        event_id: eventId || null,
        product_ids: productIds,
        min_order_amount: minOrder ? Number(minOrder) : null,
        usage_limit: usageLimit ? Number(usageLimit) : null,
        per_buyer_limit: perBuyerLimit ? Number(perBuyerLimit) : null,
        starts_at: startsAt ? new Date(startsAt).toISOString() : null,
        ends_at: endsAt ? new Date(endsAt).toISOString() : null,
      });
      setCode("");
      setDescription("");
      setProductIdsRaw("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Create failed");
    }
  }

  async function togglePause(row: MerchDiscountCode) {
    try {
      await updateHostMerchDiscount(row.id, {
        status: row.status === "active" ? "paused" : "active",
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    }
  }

  async function onArchive(row: MerchDiscountCode) {
    try {
      await archiveHostMerchDiscount(row.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Archive failed");
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title="Merch discount codes"
        description="Separate from ticket promos. Usage counts only after verified payment."
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        <Card className="mb-8 max-w-2xl space-y-4">
          <SectionHeader
            title="Create merch discount"
            description="Percent, fixed amount, or free shipping for merch checkout."
          />
          <form className="space-y-4" onSubmit={onCreate}>
            <Input
              label="Code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              hint="Stored uppercase — e.g. MERCH10"
              required
            />
            <Input
              label="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Select
                label="Discount type"
                value={discountType}
                onChange={(e) => setDiscountType(e.target.value)}
              >
                <option value="percent">Percent</option>
                <option value="fixed_amount">Fixed amount</option>
                <option value="free_shipping">Free shipping</option>
              </Select>
              <Input
                label={
                  discountType === "percent"
                    ? "Percent"
                    : discountType === "free_shipping"
                      ? "Value (unused)"
                      : "Amount (NGN)"
                }
                type="number"
                value={discountValue}
                onChange={(e) => setDiscountValue(e.target.value)}
                disabled={discountType === "free_shipping"}
                required={discountType !== "free_shipping"}
              />
            </div>
            <Select
              label="Applies to"
              value={appliesTo}
              onChange={(e) => setAppliesTo(e.target.value)}
            >
              <option value="merch_only">Merch only</option>
              <option value="bundles_only">Bundles only</option>
              <option value="tickets_and_merch">Tickets and merch</option>
              <option value="specific_event_merch">Specific event merch</option>
              <option value="host_storefront_merch">Host storefront merch</option>
              <option value="specific_products">Specific products</option>
            </Select>
            <Select
              label="Event (optional / required for event merch)"
              value={eventId}
              onChange={(e) => setEventId(e.target.value)}
            >
              <option value="">Any / none</option>
              {events.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.title}
                </option>
              ))}
            </Select>
            {appliesTo === "specific_products" ? (
              <Input
                label="Product IDs"
                value={productIdsRaw}
                onChange={(e) => setProductIdsRaw(e.target.value)}
                hint="Comma-separated product UUIDs."
                required
              />
            ) : null}
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Min eligible amount (optional)"
                type="number"
                value={minOrder}
                onChange={(e) => setMinOrder(e.target.value)}
              />
              <Input
                label="Usage limit (optional)"
                type="number"
                value={usageLimit}
                onChange={(e) => setUsageLimit(e.target.value)}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Per-buyer limit (optional)"
                type="number"
                value={perBuyerLimit}
                onChange={(e) => setPerBuyerLimit(e.target.value)}
              />
              <Input
                label="Starts at (optional)"
                type="datetime-local"
                value={startsAt}
                onChange={(e) => setStartsAt(e.target.value)}
              />
            </div>
            <Input
              label="Ends at (optional)"
              type="datetime-local"
              value={endsAt}
              onChange={(e) => setEndsAt(e.target.value)}
            />
            <Button type="submit">Create discount</Button>
          </form>
        </Card>

        <div className="space-y-4">
          <SectionHeader
            title="Your codes"
            description={`${rows.length} active merch discount${rows.length === 1 ? "" : "s"}.`}
          />
          {rows.length === 0 ? (
            <EmptyState
              title="No merch discounts yet"
              description="Create a code to reward merch buyers without touching ticket promos."
            />
          ) : (
            <div className="space-y-3">
              {rows.map((row) => (
                <Card key={row.id} className="space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="font-mono text-lg font-extrabold tracking-tight text-foreground">
                        {row.code}
                      </p>
                      <p className="text-sm font-semibold text-muted-foreground">
                        {discountLabel(row)}
                        {row.description ? ` · ${row.description}` : ""}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Applies to {row.applies_to.replace(/_/g, " ")}
                      </p>
                    </div>
                    <StatusBadge status={row.status} />
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                    <span>
                      Used {row.usage_count}
                      {row.usage_limit != null ? ` / ${row.usage_limit}` : ""}
                    </span>
                    {row.per_buyer_limit != null ? (
                      <span>Per buyer {row.per_buyer_limit}</span>
                    ) : null}
                    {row.ends_at ? (
                      <span>Ends {formatDate(row.ends_at)}</span>
                    ) : (
                      <span>No expiry</span>
                    )}
                    {row.currency ? (
                      <Badge tone="neutral" size="sm">
                        {row.currency}
                      </Badge>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2 border-t border-border pt-3">
                    {row.status === "active" || row.status === "paused" ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => void togglePause(row)}
                      >
                        {row.status === "active" ? "Pause" : "Activate"}
                      </Button>
                    ) : null}
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => void onArchive(row)}
                    >
                      Archive
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
