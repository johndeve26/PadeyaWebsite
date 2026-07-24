"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminEventBuyersExportModal } from "@/components/admin/AdminEventBuyersExportModal";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  SectionHeader,
  Select,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminEventBuyers,
  type AdminBuyerFilters,
  type AdminEventBuyerRow,
  type AdminEventBuyersResponse,
} from "@/lib/admin-event-buyers-api";
import { formatDate, formatDateTime, formatNgn } from "@/lib/format";

type Mode = "buyers" | "attendees";

const STATUS_OPTIONS = [
  { value: "", label: "Any status" },
  { value: "active", label: "Active" },
  { value: "checked_in", label: "Checked in" },
  { value: "cancelled", label: "Cancelled" },
  { value: "transferred", label: "Transferred" },
  { value: "refunded", label: "Refunded" },
];

const PAYMENT_OPTIONS = [
  { value: "", label: "Any payment" },
  { value: "success", label: "Success" },
  { value: "pending", label: "Pending" },
  { value: "failed", label: "Failed" },
];

const REFUND_OPTIONS = [
  { value: "", label: "Any refund" },
  { value: "requested", label: "Requested" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

export function AdminEventBuyersPanel({
  eventId,
  mode,
}: {
  eventId: string;
  mode: Mode;
}) {
  const [meta, setMeta] = useState<Omit<AdminEventBuyersResponse, "items"> | null>(
    null,
  );
  const [items, setItems] = useState<AdminEventBuyerRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [q, setQ] = useState("");
  const [ticketStatus, setTicketStatus] = useState("");
  const [ticketType, setTicketType] = useState("");
  const [paymentStatus, setPaymentStatus] = useState("");
  const [refundStatus, setRefundStatus] = useState("");
  const [promoCode, setPromoCode] = useState("");
  const [ambassadorCode, setAmbassadorCode] = useState("");
  const [purchasedFrom, setPurchasedFrom] = useState("");
  const [purchasedTo, setPurchasedTo] = useState("");
  const [checkedIn, setCheckedIn] = useState(
    mode === "attendees" ? "true" : "",
  );

  const filters: AdminBuyerFilters = useMemo(
    () => ({
      q: q.trim() || undefined,
      ticket_status: ticketStatus || undefined,
      ticket_type: ticketType.trim() || undefined,
      payment_status: paymentStatus || undefined,
      refund_status: refundStatus || undefined,
      promo_code: promoCode.trim() || undefined,
      ambassador_code: ambassadorCode.trim() || undefined,
      purchased_from: purchasedFrom || undefined,
      purchased_to: purchasedTo || undefined,
      checked_in: checkedIn || undefined,
      limit: 500,
    }),
    [
      q,
      ticketStatus,
      ticketType,
      paymentStatus,
      refundStatus,
      promoCode,
      ambassadorCode,
      purchasedFrom,
      purchasedTo,
      checkedIn,
    ],
  );

  const load = useCallback(async () => {
    setError(null);
    const data = await fetchAdminEventBuyers(eventId, filters);
    setItems(data.items);
    setMeta({
      event_id: data.event_id,
      event_title: data.event_title,
      event_slug: data.event_slug,
      event_date: data.event_date,
      host_name: data.host_name,
      host_id: data.host_id,
      total: data.total,
      limit: data.limit,
      offset: data.offset,
    });
  }, [eventId, filters]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load buyers");
          setItems([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  const typeOptions = useMemo(() => {
    const set = new Set<string>();
    for (const row of items || []) {
      const name = row.ticket_type || row.ticket_type_name;
      if (name) set.add(name);
    }
    return Array.from(set).sort();
  }, [items]);

  const total = meta?.total ?? 0;

  return (
    <div className="space-y-4">
      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Export ready">
          {note}
        </Alert>
      ) : null}

      <Card className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <SectionHeader
              title={mode === "attendees" ? "Checked-in attendees" : "Buyers"}
              description={
                mode === "attendees"
                  ? "Ticket holders who checked in. Public profile + ticket fields only in the list."
                  : "Issued tickets for this event. Filter, then export with an audited mode."
              }
              className="pb-0"
            />
            <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
              <div>
                <dt className="inline font-semibold text-foreground">Event: </dt>
                <dd className="inline">
                  {meta?.event_title || "Loading…"}
                </dd>
              </div>
              <div>
                <dt className="inline font-semibold text-foreground">Host: </dt>
                <dd className="inline">{meta?.host_name || "—"}</dd>
              </div>
              <div>
                <dt className="inline font-semibold text-foreground">Date: </dt>
                <dd className="inline">{formatDate(meta?.event_date)}</dd>
              </div>
              <div>
                <dt className="inline font-semibold text-foreground">Buyers: </dt>
                <dd className="inline tabular-nums">{total}</dd>
              </div>
            </dl>
          </div>
          <Button size="sm" onClick={() => setExportOpen(true)}>
            Export
          </Button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            label="Search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Username, display name, ticket code…"
          />
          <Select
            label="Ticket status"
            value={ticketStatus}
            onChange={(e) => setTicketStatus(e.target.value)}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value || "any"} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>
          <Select
            label="Check-in"
            value={checkedIn}
            onChange={(e) => setCheckedIn(e.target.value)}
          >
            <option value="">Any</option>
            <option value="true">Checked in</option>
            <option value="false">Not checked in</option>
          </Select>
          <Select
            label="Ticket type"
            value={ticketType}
            onChange={(e) => setTicketType(e.target.value)}
          >
            <option value="">Any type</option>
            {typeOptions.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </Select>
          <Select
            label="Payment status"
            value={paymentStatus}
            onChange={(e) => setPaymentStatus(e.target.value)}
          >
            {PAYMENT_OPTIONS.map((opt) => (
              <option key={opt.value || "pay-any"} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>
          <Select
            label="Refund status"
            value={refundStatus}
            onChange={(e) => setRefundStatus(e.target.value)}
          >
            {REFUND_OPTIONS.map((opt) => (
              <option key={opt.value || "ref-any"} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>
          <Input
            label="Promo code"
            value={promoCode}
            onChange={(e) => setPromoCode(e.target.value)}
            placeholder="e.g. WELCOME10"
          />
          <Input
            label="Ambassador code"
            value={ambassadorCode}
            onChange={(e) => setAmbassadorCode(e.target.value)}
            placeholder="Referral / ambassador"
          />
          <Input
            label="Purchased from"
            type="date"
            value={purchasedFrom}
            onChange={(e) => setPurchasedFrom(e.target.value)}
          />
          <Input
            label="Purchased to"
            type="date"
            value={purchasedTo}
            onChange={(e) => setPurchasedTo(e.target.value)}
          />
        </div>

        <p className="text-xs font-semibold tabular-nums text-muted-foreground">
          {items === null
            ? "Loading…"
            : `${total} matching ticket${total === 1 ? "" : "s"}`}
        </p>
      </Card>

      {items === null ? (
        <SkeletonLoader lines={6} />
      ) : items.length === 0 ? (
        <EmptyState
          title={mode === "attendees" ? "No check-ins yet" : "No buyers match"}
          description="Try clearing filters or wait for paid ticket issuance."
        />
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-border text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Buyer</th>
                <th className="px-3 py-3">Username</th>
                <th className="px-3 py-3">Ticket type</th>
                <th className="px-3 py-3">Quantity</th>
                <th className="px-3 py-3">Paid</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Checked in</th>
                <th className="px-3 py-3">Promo / Ambassador</th>
                <th className="px-3 py-3">Purchased at</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => {
                const buyerName =
                  row.display_name ||
                  row.passport_display_name ||
                  row.attendee_name ||
                  row.holder_name ||
                  "—";
                const username =
                  row.username || row.passport_username || null;
                const paid = row.amount_paid || row.order_total_amount;
                const currency = row.currency || row.order_currency;
                const promo = row.promo_code_used || row.promo_code;
                const purchased =
                  row.purchase_date || row.order_paid_at || row.ticket_created_at;
                return (
                  <tr
                    key={row.ticket_id}
                    className="border-b border-border/70 last:border-b-0"
                  >
                    <td className="px-4 py-3 font-semibold text-foreground">
                      {buyerName}
                    </td>
                    <td className="px-3 py-3 text-muted-foreground">
                      {username ? `@${username}` : "—"}
                    </td>
                    <td className="px-3 py-3 text-foreground">
                      {row.ticket_type || row.ticket_type_name}
                    </td>
                    <td className="px-3 py-3 tabular-nums text-foreground">
                      {row.quantity ?? 1}
                    </td>
                    <td className="px-3 py-3 text-foreground">
                      {paid
                        ? currency && currency !== "NGN"
                          ? `${paid} ${currency}`
                          : formatNgn(paid)
                        : "—"}
                    </td>
                    <td className="px-3 py-3">
                      <StatusBadge
                        status={row.purchase_status || row.ticket_status}
                      />
                    </td>
                    <td className="px-3 py-3">
                      {row.is_checked_in || row.checked_in ? (
                        <Badge tone="success" size="sm">
                          {row.checked_in_at
                            ? formatDateTime(row.checked_in_at)
                            : "Checked in"}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-xs text-muted-foreground">
                      {[promo, row.ambassador_code].filter(Boolean).join(" · ") ||
                        "—"}
                    </td>
                    <td className="px-3 py-3 text-xs text-muted-foreground">
                      {formatDateTime(purchased)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}

      <AdminEventBuyersExportModal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        eventId={eventId}
        filters={filters}
        onExported={() => setNote("Export downloaded. This action was audited.")}
      />
    </div>
  );
}
