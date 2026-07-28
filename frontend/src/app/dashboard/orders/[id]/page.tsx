"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { StartMessageButton } from "@/components/messaging/StartMessageButton";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import {
  cancelBuyerOrder,
  confirmCheckoutPayment,
  downloadOrderPdf,
  fetchOrder,
  resendOrderTicketEmails,
} from "@/lib/commerce-api";
import { ApiError } from "@/lib/api";
import { formatDateTime, formatNgn } from "@/lib/format";
import type { Order } from "@/lib/types/commerce";

export default function OrderReceiptPage() {
  const params = useParams<{ id: string }>();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmHint, setConfirmHint] = useState<string | null>(null);
  const [resendMessage, setResendMessage] = useState<string | null>(null);
  const [resendBusy, setResendBusy] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);
  const [cancelMessage, setCancelMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        let item = await fetchOrder(params.id);
        if (item.status === "pending") {
          try {
            item = await confirmCheckoutPayment(item.id);
            if (active) setConfirmHint(null);
          } catch (err) {
            if (active && err instanceof ApiError && err.detail) {
              setConfirmHint(err.detail);
            }
          }
        } else if (active) {
          setConfirmHint(null);
        }
        if (active) setOrder(item);
      } catch {
        if (active) setError("Order not found.");
      }
    };
    void load();
    const timer = window.setInterval(() => {
      void load();
    }, 4000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [params.id]);

  if (error) {
    return (
      <DashboardShell
        tone="soft"
        eyebrow="Receipt"
        title="Unavailable"
        description="This order could not be loaded."
        actions={
          <Link href="/dashboard/orders">
            <Button variant="secondary">All orders</Button>
          </Link>
        }
      >
        <EmptyState title="Order not found" description={error} />
      </DashboardShell>
    );
  }

  if (!order) {
    return (
      <DashboardShell
        tone="soft"
        eyebrow="Receipt"
        title="Loading receipt…"
        description="If you just paid, wait for payment confirmation — tickets are not issued from the browser."
      >
        <SkeletonLoader lines={5} />
      </DashboardShell>
    );
  }

  const discount = Number(order.discount_amount ?? 0);
  const merchItems = order.items.filter(
    (item) => item.item_kind === "merch" || Boolean(item.merch_variant_id),
  );
  const hasMerch = merchItems.length > 0;
  const boughtForSomeoneElse = Boolean(
    order?.is_gift ||
      order?.purchased_for_someone_else ||
      order?.purchase_mode === "other" ||
      order?.purchase_mode === "group",
  );

  async function onResendRecipientEmail() {
    if (!order) return;
    setResendBusy(true);
    setResendMessage(null);
    try {
      const result = await resendOrderTicketEmails(order.id);
      setResendMessage(result.detail);
    } catch (err) {
      setResendMessage(
        err instanceof ApiError ? err.detail : "Could not resend ticket emails.",
      );
    } finally {
      setResendBusy(false);
    }
  }

  async function onDownloadPdf() {
    if (!order) return;
    setPdfBusy(true);
    try {
      await downloadOrderPdf(order.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not download PDF.");
    } finally {
      setPdfBusy(false);
    }
  }

  async function onCancelPendingOrder() {
    if (!order || order.status !== "pending" || cancelBusy) return;
    setCancelBusy(true);
    setCancelMessage(null);
    try {
      const updated = await cancelBuyerOrder(order.id);
      setOrder(updated);
      setConfirmHint(null);
      setCancelMessage("Order cancelled. Reserved tickets were released.");
    } catch (err) {
      setCancelMessage(
        err instanceof ApiError ? err.detail : "Could not cancel this order.",
      );
    } finally {
      setCancelBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Receipt"
      title={order.event_title ?? "Order receipt"}
      description={`Reference ${order.reference}`}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={order.status} />
          {order.status === "paid" ? (
            <>
              <Link href="/dashboard/tickets">
                <Button size="sm">View tickets</Button>
              </Link>
              {hasMerch ? (
                <Link href="/dashboard/merchandise">
                  <Button size="sm" variant="secondary">
                    View merch
                  </Button>
                </Link>
              ) : null}
              <Button
                size="sm"
                variant="secondary"
                disabled={pdfBusy}
                onClick={() => void onDownloadPdf()}
              >
                {pdfBusy ? "…" : "Download PDF"}
              </Button>
            </>
          ) : null}
          <Link href="/dashboard/orders">
            <Button variant="secondary" size="sm">
              All orders
            </Button>
          </Link>
        </div>
      }
    >
      {order.status !== "paid" ? (
        <Alert tone="warning" title="Confirming your payment">
          We&apos;re double-checking with your bank. This page updates automatically —
          your tickets and merch appear as soon as payment is confirmed.
          {confirmHint ? (
            <span className="mt-2 block text-foreground">{confirmHint}</span>
          ) : null}
          {order.status === "pending" ? (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                variant="secondary"
                disabled={cancelBusy}
                onClick={() => void onCancelPendingOrder()}
              >
                {cancelBusy ? "Cancelling…" : "Cancel unpaid order"}
              </Button>
              {cancelMessage ? (
                <span className="text-sm text-foreground">{cancelMessage}</span>
              ) : null}
            </div>
          ) : null}
        </Alert>
      ) : (
        <Alert tone="success" title="Paid">
          {order.paid_at
            ? `Confirmed ${formatDateTime(order.paid_at)}`
            : "Payment confirmed."}
        </Alert>
      )}

      {order.status === "cancelled" && cancelMessage ? (
        <Alert tone="info" title="Order cancelled">
          {cancelMessage}
        </Alert>
      ) : null}

      {order.status === "paid" && boughtForSomeoneElse ? (
        <Card className="space-y-3">
          <h3 className="text-lg font-extrabold text-foreground">
            Ticket for someone else
          </h3>
          <p className="text-sm text-muted-foreground">
            {order.recipient_email ? (
              <>
                We send ticket details to{" "}
                <span className="font-semibold text-foreground">
                  {order.recipient_email}
                </span>{" "}
                after payment confirms. They should create a Pàdéyá account with
                that same email, then open My tickets — or you can transfer the
                pass from your tickets page.
              </>
            ) : (
              <>
                Attendee emails on this order receive their own notification after
                payment confirms.
              </>
            )}
          </p>
          <Button
            size="sm"
            variant="secondary"
            disabled={resendBusy}
            onClick={() => void onResendRecipientEmail()}
          >
            {resendBusy ? "Sending…" : "Resend ticket emails"}
          </Button>
          {resendMessage ? (
            <p className="text-sm text-muted-foreground">{resendMessage}</p>
          ) : null}
        </Card>
      ) : null}

      <Card className="space-y-1 bg-ink text-paper">
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">
          Pàdéyá receipt
        </p>
        <p className="text-2xl font-extrabold tracking-tight">
          {formatNgn(order.total_amount)}{" "}
          <span className="text-base font-semibold text-subtle-foreground">
            {order.currency}
          </span>
        </p>
        <p className="text-sm text-subtle-foreground">
          {order.buyer_name} · {order.buyer_email}
        </p>
      </Card>

      <Card className="space-y-2">
        <h3 className="text-lg font-extrabold text-foreground">Event & host</h3>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
          {order.event_slug ? (
            <Link
              href={`/events/${order.event_slug}`}
              className="font-bold text-foreground underline-offset-2 hover:underline"
            >
              {order.event_title ?? "Event"}
            </Link>
          ) : (
            <p className="font-bold text-foreground">
              {order.event_title ?? "Event"}
            </p>
          )}
          {order.host_slug ? (
            <Link
              href={`/u/${order.host_slug}`}
              className="text-muted-foreground underline-offset-2 hover:underline"
            >
              {order.host_name ?? "Host"}
            </Link>
          ) : order.host_name ? (
            <p className="text-muted-foreground">{order.host_name}</p>
          ) : null}
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-4">
          <h3 className="text-lg font-extrabold text-foreground">Items</h3>
          <ul className="space-y-3">
            {order.items.map((item) => {
              const isMerch =
                item.item_kind === "merch" || Boolean(item.merch_variant_id);
              const title = isMerch
                ? item.product_name || "Merch"
                : item.ticket_type_name || "Ticket";
              return (
                <li
                  key={item.id}
                  className="space-y-1 border-b border-border pb-3 last:border-0 last:pb-0"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-bold text-foreground">{title}</p>
                      {isMerch && item.variant_label ? (
                        <p className="text-sm text-muted-foreground">
                          Variant: {item.variant_label}
                        </p>
                      ) : null}
                      <p className="text-sm text-muted-foreground">
                        Qty {item.quantity}
                      </p>
                      {isMerch ? (
                        <div className="mt-1 space-y-1 text-xs text-muted-foreground">
                          {item.fulfillment_status ? (
                            <p className="flex flex-wrap items-center gap-2">
                              <StatusBadge status={item.fulfillment_status} />
                              {item.pickup_code ? (
                                <Badge tone="outline">{item.pickup_code}</Badge>
                              ) : null}
                            </p>
                          ) : (
                            <p>Pickup details appear after payment confirms.</p>
                          )}
                          {item.pickup_instructions ? (
                            <p>Pickup: {item.pickup_instructions}</p>
                          ) : null}
                          {order.host_id ? (
                            <div className="pt-1">
                              <StartMessageButton
                                hostId={order.host_id}
                                hostUsername={order.host_slug || undefined}
                                relatedEventId={order.event_id || undefined}
                                relatedMerchOrderItemId={item.id}
                                productName={
                                  item.product_name || title || undefined
                                }
                                label="Message host"
                                size="sm"
                                variant="ghost"
                                returnPath={`/dashboard/orders/${order.id}`}
                              />
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                    <p className="font-bold tabular-nums text-foreground">
                      {formatNgn(item.line_total)}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="space-y-1 border-t border-border pt-3 text-sm">
            <div className="flex justify-between text-muted-foreground">
              <span>Subtotal</span>
              <span className="tabular-nums">
                {formatNgn(order.subtotal_amount)}
              </span>
            </div>
            {discount > 0 ? (
              <div className="flex justify-between text-success">
                <span>
                  Discount
                  {order.promo_code_snapshot
                    ? ` (${order.promo_code_snapshot})`
                    : ""}
                </span>
                <span className="tabular-nums">−{formatNgn(discount)}</span>
              </div>
            ) : null}
            {(order.fee_breakdown ?? [])
              .filter((line) => line.payer === "buyer")
              .map((line) => (
                <div
                  key={line.fee_key}
                  className="flex justify-between text-muted-foreground"
                >
                  <span>{line.label}</span>
                  <span className="tabular-nums">
                    {formatNgn(Number(line.amount))}
                  </span>
                </div>
              ))}
            {Number(order.buyer_fee_total ?? 0) > 0 &&
            !(order.fee_breakdown ?? []).some((line) => line.payer === "buyer") ? (
              <div className="flex justify-between text-muted-foreground">
                <span>Service fee</span>
                <span className="tabular-nums">
                  {formatNgn(Number(order.buyer_fee_total))}
                </span>
              </div>
            ) : null}
            <div className="flex justify-between pt-1 text-xl font-extrabold text-foreground">
              <span>Total</span>
              <span className="tabular-nums">
                {formatNgn(order.final_total ?? order.total_amount)}
              </span>
            </div>
          </div>
        </Card>

        <Card className="space-y-4">
          <h3 className="text-lg font-extrabold text-foreground">
            Payment timeline
          </h3>
          {order.payments.length === 0 ? (
            <p className="text-base text-muted-foreground">
              No payment attempts yet.
            </p>
          ) : (
            <ul className="space-y-4">
              {order.payments.map((payment) => (
                <li
                  key={payment.id}
                  className="space-y-1 border-b border-border pb-3 last:border-0"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-bold text-foreground">
                      {payment.provider}
                    </span>
                    <StatusBadge status={payment.status} />
                  </div>
                  <p className="text-base font-bold tabular-nums text-foreground">
                    {formatNgn(payment.amount)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {formatDateTime(payment.paid_at ?? payment.created_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {(order.checkout_answers?.length ?? 0) > 0 ? (
        <Card className="space-y-4">
          <h3 className="text-lg font-extrabold text-foreground">
            Your answers
          </h3>
          <ul className="space-y-3">
            {order.checkout_answers?.map((answer) => (
              <li
                key={answer.id}
                className="border-b border-border pb-3 last:border-0 last:pb-0"
              >
                <p className="text-sm text-muted-foreground">
                  {answer.question_label}
                </p>
                <p className="font-semibold text-foreground">{answer.value}</p>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </DashboardShell>
  );
}
