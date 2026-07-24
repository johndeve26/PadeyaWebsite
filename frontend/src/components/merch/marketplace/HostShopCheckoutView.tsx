"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { RestrictedActionNotice } from "@/components/account/RestrictedActionNotice";
import { CheckoutTrustStrip } from "@/components/checkout/CheckoutTrustStrip";
import {
  emptyShippingAddress,
  isShippingAddressComplete,
  ShippingAddressForm,
  shippingAddressToApiPayload,
  type ShippingAddressValues,
} from "@/components/merch/ShippingAddressForm";
import {
  Alert,
  Button,
  Container,
  EmptyState,
  Input,
  QuantityInput,
  SkeletonLoader,
} from "@/components/ui";
import { useHostAffiliation } from "@/hooks/useHostAffiliation";
import { useUserRestrictions } from "@/hooks/useUserRestrictions";
import { ApiError } from "@/lib/api";
import { trackMerchCheckoutStarted } from "@/lib/analytics";
import {
  checkoutOrder,
  confirmCheckoutPayment,
  createOrder,
  fetchPaystackConfig,
  isPaystackCompatibleEmail,
  quoteBuyerFees,
  type BuyerFeeQuote,
} from "@/lib/commerce-api";
import { formatNgn } from "@/lib/format";
import {
  addBuyerCartItem,
  fetchBuyerCart,
  fetchMerchHostShop,
  removeBuyerCartItem,
  updateBuyerCartItemQuantity,
} from "@/lib/merch-api";
import { variantAvailable } from "@/lib/merch-stock";
import { openPaystackPopup } from "@/lib/paystack-inline";
import type { MarketplaceHostShopDetail, MarketplaceProduct } from "@/lib/types/merch";

type MerchLine = {
  product: MarketplaceProduct;
  variantId: string;
  quantity: number;
  cartItemId?: string | null;
};

type Props = {
  username: string;
};

function findVariant(product: MarketplaceProduct, variantId: string) {
  return product.variants.find((v) => v.id === variantId) ?? null;
}

function lineMaxQty(
  product: MarketplaceProduct,
  variant: NonNullable<ReturnType<typeof findVariant>>,
) {
  const available = variantAvailable(variant);
  return Math.max(
    1,
    Math.min(
      available,
      product.max_per_order ?? product.max_per_buyer ?? available,
    ),
  );
}

function buildSingleLine(
  shop: MarketplaceHostShopDetail,
  variantId: string,
  quantity: number,
  cartItemId?: string | null,
): MerchLine | null {
  const products = shop.products ?? [];
  const product = products.find((p) => p.variants.some((v) => v.id === variantId));
  if (!product) return null;
  const variant = findVariant(product, variantId);
  if (!variant || variantAvailable(variant) <= 0) return null;
  const max = lineMaxQty(product, variant);
  const qty = Math.min(Math.max(1, quantity), max);
  return { product, variantId: variant.id, quantity: qty, cartItemId };
}

function buildLinesFromCart(
  shop: MarketplaceHostShopDetail,
  cartItems: Array<{ id: string; variant_id: string; quantity: number }>,
): MerchLine[] {
  const merged = new Map<string, MerchLine>();
  for (const item of cartItems) {
    const existing = merged.get(item.variant_id);
    if (existing) {
      existing.quantity += item.quantity;
      if (!existing.cartItemId) {
        existing.cartItemId = item.id;
      }
      continue;
    }
    const line = buildSingleLine(shop, item.variant_id, item.quantity, item.id);
    if (line) {
      merged.set(item.variant_id, line);
    }
  }
  return Array.from(merged.values()).map((line) => {
    const variant = findVariant(line.product, line.variantId);
    if (!variant) return line;
    const max = lineMaxQty(line.product, variant);
    return { ...line, quantity: Math.min(line.quantity, max) };
  });
}

function mergePrefillLine(
  lines: MerchLine[],
  shop: MarketplaceHostShopDetail,
  variantId: string,
  quantity: number,
  productId?: string,
): MerchLine[] {
  const existing = lines.find((line) => line.variantId === variantId);
  if (existing) {
    const variant = findVariant(existing.product, variantId);
    if (!variant) return lines;
    const max = lineMaxQty(existing.product, variant);
    return lines.map((line) =>
      line.variantId === variantId
        ? { ...line, quantity: Math.min(max, line.quantity + quantity) }
        : line,
    );
  }

  const products = shop.products ?? [];
  const product =
    products.find((p) => p.variants.some((v) => v.id === variantId)) ??
    (productId ? products.find((p) => p.id === productId) : undefined);
  if (!product) return lines;
  const line = buildSingleLine(shop, variantId, quantity);
  return line ? [...lines, line] : lines;
}

export function HostShopCheckoutView({ username }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();
  const restrictions = useUserRestrictions();
  const [shop, setShop] = useState<MarketplaceHostShopDetail | null>(null);
  const [lines, setLines] = useState<MerchLine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [feeQuote, setFeeQuote] = useState<BuyerFeeQuote | null>(null);
  const [fulfillmentMethod, setFulfillmentMethod] = useState<"pickup" | "shipping">(
    "pickup",
  );
  const [shippingAddress, setShippingAddress] =
    useState<ShippingAddressValues>(emptyShippingAddress);
  const [paymentEmail, setPaymentEmail] = useState("");
  const [paystackPublicKey, setPaystackPublicKey] = useState<string | null>(null);
  const paymentStartedRef = useRef(false);

  const hostId = shop?.host_id ?? shop?.host?.id ?? null;
  const hostSlug =
    shop?.host_slug ?? shop?.host?.slug ?? shop?.host_username ?? username;
  const hostName =
    shop?.host_name ?? shop?.host?.display_name ?? shop?.host?.name ?? "Host shop";

  const { affiliated: isOwnHost } = useHostAffiliation({
    hostId,
    hostSlug,
  });

  const checkoutBlocked = restrictions.has("cannot_checkout");

  const prefillMerchId = (searchParams.get("merch") || "").trim();
  const prefillVariantId = (searchParams.get("variant") || "").trim();
  const prefillQty = Math.max(
    1,
    Number.parseInt(searchParams.get("qty") || "1", 10) || 1,
  );

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      const next = `/merch/hosts/${username}/checkout${
        searchParams.toString() ? `?${searchParams.toString()}` : ""
      }`;
      router.replace(`/login?next=${encodeURIComponent(next)}`);
    }
  }, [authLoading, user, username, searchParams, router]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [shopRow, cartRow, paystack] = await Promise.all([
          fetchMerchHostShop(username),
          fetchBuyerCart().catch(() => null),
          fetchPaystackConfig().catch(() => null),
        ]);
        if (!active) return;
        setShop(shopRow);
        setPaystackPublicKey(paystack?.public_key ?? null);

        let nextLines: MerchLine[] = [];

        const cartHostMatches =
          cartRow?.host_id &&
          shopRow.host_id &&
          cartRow.host_id === shopRow.host_id &&
          (cartRow.items?.length ?? 0) > 0;

        if (cartHostMatches && cartRow?.items) {
          nextLines = buildLinesFromCart(shopRow, cartRow.items);
        }

        if (prefillVariantId) {
          nextLines = mergePrefillLine(
            nextLines,
            shopRow,
            prefillVariantId,
            prefillQty,
            prefillMerchId || undefined,
          );
        }

        setLines(nextLines);
        const anyShips = nextLines.some((row) => row.product.shipping_enabled);
        const anyPickup = nextLines.some(
          (row) => row.product.pickup_enabled !== false,
        );
        setFulfillmentMethod(
          anyShips && !anyPickup ? "shipping" : "pickup",
        );
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError ? err.detail : "Could not load host checkout",
        );
        setShop(null);
        setLines([]);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [username, prefillMerchId, prefillVariantId, prefillQty]);

  const selectedMerch = useMemo(
    () =>
      lines
        .map((row) => {
          const variant = findVariant(row.product, row.variantId);
          if (!variant) return null;
          return { ...row, variant };
        })
        .filter((row): row is MerchLine & { variant: NonNullable<ReturnType<typeof findVariant>> } =>
          Boolean(row),
        ),
    [lines],
  );

  const merchSubtotal = selectedMerch.reduce(
    (sum, row) => sum + Number(row.variant.effective_price) * row.quantity,
    0,
  );
  const merchShippingAvailable = selectedMerch.some(
    (row) => row.product.shipping_enabled,
  );
  const merchPickupAvailable = selectedMerch.some(
    (row) => row.product.pickup_enabled !== false,
  );
  const effectiveFulfillment =
    fulfillmentMethod === "shipping" && merchShippingAvailable
      ? "shipping"
      : "pickup";
  const needsShippingAddress = effectiveFulfillment === "shipping";
  const total = feeQuote
    ? Number(feeQuote.final_total)
    : Math.max(0, merchSubtotal);

  const accountEmailNeedsPaystackOverride = Boolean(
    user?.email && !isPaystackCompatibleEmail(user.email),
  );
  const paystackCustomerEmail = accountEmailNeedsPaystackOverride
    ? paymentEmail.trim()
    : (user?.email || "").trim();

  useEffect(() => {
    let active = true;
    const handle = window.setTimeout(() => {
      void (async () => {
        if (!hostId || merchSubtotal <= 0) {
          if (active) setFeeQuote(null);
          return;
        }
        try {
          const quote = await quoteBuyerFees({
            host_id: hostId,
            merch_subtotal: merchSubtotal,
            shipping_amount: needsShippingAddress ? 0 : 0,
          });
          if (active) setFeeQuote(quote);
        } catch {
          if (active) setFeeQuote(null);
        }
      })();
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(handle);
    };
  }, [hostId, merchSubtotal, needsShippingAddress]);

  async function syncCartQuantity(line: MerchLine, quantity: number) {
    try {
      // Cart lines already in the buyer's cart get an exact-quantity PATCH;
      // add_cart_item is additive, so reusing it here would compound quantities
      // (e.g. bumping 1 -> 2 would leave 1 + 2 = 3 items in the cart).
      const cart = line.cartItemId
        ? await updateBuyerCartItemQuantity(line.cartItemId, quantity)
        : await addBuyerCartItem(line.variantId, quantity);
      const cartItem = cart.items.find((item) => item.variant_id === line.variantId);
      if (cartItem) {
        setLines((prev) =>
          prev.map((row) =>
            row.variantId === line.variantId
              ? { ...row, quantity, cartItemId: cartItem.id }
              : row,
          ),
        );
      }
    } catch {
      /* checkout can still proceed with local line quantities */
    }
  }

  function updateLineQuantity(
    line: MerchLine & { variant: NonNullable<ReturnType<typeof findVariant>> },
    quantity: number,
  ) {
    const max = lineMaxQty(line.product, line.variant);
    const next = Math.min(max, Math.max(1, quantity));
    setLines((prev) =>
      prev.map((row) =>
        row.variantId === line.variantId ? { ...row, quantity: next } : row,
      ),
    );
    void syncCartQuantity(line, next);
  }

  async function removeLine(line: MerchLine) {
    setLines((prev) => prev.filter((row) => row.variantId !== line.variantId));
    if (!line.cartItemId) return;
    try {
      await removeBuyerCartItem(line.cartItemId);
    } catch {
      /* line already removed locally */
    }
  }

  async function onPay() {
    if (!hostId || selectedMerch.length === 0) {
      setError("Add at least one merch item to checkout.");
      return;
    }
    if (needsShippingAddress && !isShippingAddressComplete(shippingAddress)) {
      setError("Enter a complete delivery address for shipping.");
      return;
    }
    if (
      accountEmailNeedsPaystackOverride &&
      total > 0 &&
      !isPaystackCompatibleEmail(paystackCustomerEmail)
    ) {
      setError(
        "Enter a standard payment email (demo @*.test addresses are not accepted by Paystack).",
      );
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const order = await createOrder({
        host_id: hostId,
        items: selectedMerch.map((row) => ({
          item_kind: "merch" as const,
          merch_variant_id: row.variant.id,
          quantity: row.quantity,
        })),
        fulfillment_method: effectiveFulfillment,
        ...(needsShippingAddress
          ? { shipping_address: shippingAddressToApiPayload(shippingAddress) }
          : {}),
      });
      paymentStartedRef.current = true;
      trackMerchCheckoutStarted({
        targetEventId: hostId,
        hostId,
        orderId: order.id,
        merchItemCount: selectedMerch.reduce((n, row) => n + row.quantity, 0),
        fulfillmentMethod: effectiveFulfillment,
      });

      const checkout = await checkoutOrder(
        order.id,
        accountEmailNeedsPaystackOverride && total > 0
          ? { payment_email: paystackCustomerEmail }
          : undefined,
      );

      if (checkout.free_checkout) {
        router.push(`/dashboard/orders/${order.id}`);
        return;
      }

      const paystackEmail = (
        checkout.paystack_customer_email || paystackCustomerEmail
      )
        .trim()
        .toLowerCase();

      if (!isPaystackCompatibleEmail(paystackEmail)) {
        setError("Use a standard email for payment (for example Gmail or work email).");
        paymentStartedRef.current = false;
        return;
      }

      const amountKobo = Math.round(
        Number(checkout.final_total ?? checkout.amount) * 100,
      );
      if (!Number.isFinite(amountKobo) || amountKobo <= 0) {
        setError("Could not determine order total for payment. Refresh and try again.");
        paymentStartedRef.current = false;
        return;
      }

      const publicKey = (checkout.public_key || paystackPublicKey || "").trim();
      if (checkout.access_code || publicKey) {
        if (!publicKey) {
          setError(
            "Paystack public key is missing. Set it in Admin → Payment integration.",
          );
          paymentStartedRef.current = false;
          return;
        }
        const outcome = await openPaystackPopup({
          accessCode: checkout.access_code,
          publicKey,
          email: paystackEmail,
          amountKobo,
          reference: checkout.reference,
        });
        if (outcome === "success") {
          try {
            await confirmCheckoutPayment(order.id);
          } catch {
            /* webhook may still confirm */
          }
          router.push(
            `/checkout/success?order=${encodeURIComponent(checkout.reference)}`,
          );
          return;
        }
        setError("Payment was cancelled. You can try again when ready.");
        paymentStartedRef.current = false;
        return;
      }

      if (checkout.authorization_url) {
        window.location.href = checkout.authorization_url;
        return;
      }
      setError("Checkout could not be initialized.");
      paymentStartedRef.current = false;
    } catch (err) {
      paymentStartedRef.current = false;
      setError(err instanceof ApiError ? err.detail : "Checkout failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (authLoading || loading) {
    return (
      <main className="bg-background py-16">
        <Container width="narrow">
          <SkeletonLoader lines={6} />
        </Container>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="bg-background py-16">
        <Container width="narrow">
          <SkeletonLoader lines={3} />
        </Container>
      </main>
    );
  }

  if (checkoutBlocked) {
    return (
      <main className="bg-background py-16">
        <Container width="narrow" className="space-y-4">
          <RestrictedActionNotice />
          <Link href={`/merch/hosts/${hostSlug}`}>
            <Button variant="secondary">Back to shop</Button>
          </Link>
        </Container>
      </main>
    );
  }

  if (isOwnHost) {
    return (
      <main className="bg-background py-16">
        <Container width="narrow">
          <EmptyState
            title="This is your host shop"
            description="You can't buy merch from your own host workspace."
            action={
              <Link href="/host/merchandise">
                <Button>Manage merch</Button>
              </Link>
            }
          />
        </Container>
      </main>
    );
  }

  if (error && !shop) {
    return (
      <main className="bg-background py-16">
        <Container width="narrow">
          <EmptyState
            title="Checkout unavailable"
            description={error}
            action={
              <Link href={`/merch/hosts/${username}`}>
                <Button variant="secondary">Back to shop</Button>
              </Link>
            }
          />
        </Container>
      </main>
    );
  }

  return (
    <main className="bg-background py-10 sm:py-14">
      <Container width="narrow" className="space-y-8">
        <header className="space-y-2">
          <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-muted-foreground">
            Host shop checkout
          </p>
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
            {hostName}
          </h1>
          <p className="text-sm text-muted-foreground">
            Review merch and pay securely — nothing is purchased until payment
            succeeds.
          </p>
        </header>

        {error ? (
          <Alert tone="danger" title="Checkout issue">
            {error}
          </Alert>
        ) : null}

        {selectedMerch.length === 0 ? (
          <EmptyState
            title="No items to checkout"
            description="Add merch from the host shop, then return here to pay."
            action={
              <Link href={`/merch/hosts/${hostSlug}`}>
                <Button>Browse shop</Button>
              </Link>
            }
          />
        ) : (
          <>
            <section className="space-y-3 rounded-[var(--radius-lg)] border border-border bg-card p-4 sm:p-5">
              <h2 className="text-lg font-extrabold text-foreground">Your items</h2>
              <ul className="divide-y divide-border">
                {selectedMerch.map((row) => {
                  const maxQty = lineMaxQty(row.product, row.variant);
                  return (
                    <li
                      key={row.variantId}
                      className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="font-bold text-foreground">{row.product.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {row.variant.label}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center justify-between gap-3 sm:justify-end">
                        <QuantityInput
                          value={row.quantity}
                          min={1}
                          max={maxQty}
                          aria-label={`Quantity for ${row.product.name}`}
                          onChange={(quantity) => updateLineQuantity(row, quantity)}
                        />
                        <p className="min-w-[5.5rem] text-right text-sm font-extrabold tabular-nums text-foreground">
                          {formatNgn(Number(row.variant.effective_price) * row.quantity)}
                        </p>
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          onClick={() => void removeLine(row)}
                        >
                          Remove
                        </Button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>

            {merchShippingAvailable || merchPickupAvailable ? (
              <section className="space-y-3">
                <h2 className="text-lg font-extrabold text-foreground">Fulfillment</h2>
                <div className="flex flex-wrap gap-2">
                  {merchPickupAvailable ? (
                    <Button
                      type="button"
                      size="sm"
                      variant={effectiveFulfillment === "pickup" ? undefined : "secondary"}
                      onClick={() => setFulfillmentMethod("pickup")}
                    >
                      Pickup
                    </Button>
                  ) : null}
                  {merchShippingAvailable ? (
                    <Button
                      type="button"
                      size="sm"
                      variant={
                        effectiveFulfillment === "shipping" ? undefined : "secondary"
                      }
                      onClick={() => setFulfillmentMethod("shipping")}
                    >
                      Delivery
                    </Button>
                  ) : null}
                </div>
                {effectiveFulfillment === "pickup" ? (
                  <p className="text-sm text-muted-foreground">
                    Pickup details are shared after purchase.
                  </p>
                ) : null}
              </section>
            ) : null}

            {needsShippingAddress ? (
              <section className="space-y-3">
                <h2 className="text-lg font-extrabold text-foreground">
                  Delivery address
                </h2>
                <ShippingAddressForm
                  value={shippingAddress}
                  onChange={setShippingAddress}
                />
              </section>
            ) : null}

            <section className="space-y-2 rounded-[var(--radius-lg)] border border-border bg-muted/30 p-4">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Merch subtotal</span>
                <span className="font-bold text-foreground">
                  {formatNgn(merchSubtotal)}
                </span>
              </div>
              {feeQuote ? (
                <>
                  {Number(feeQuote.buyer_fee_total) > 0 ? (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Service fees</span>
                      <span className="font-bold text-foreground">
                        {formatNgn(feeQuote.buyer_fee_total)}
                      </span>
                    </div>
                  ) : null}
                  <div className="flex justify-between border-t border-border pt-2 text-base">
                    <span className="font-extrabold text-foreground">Total</span>
                    <span className="font-extrabold text-foreground">
                      {formatNgn(feeQuote.final_total)}
                    </span>
                  </div>
                </>
              ) : (
                <div className="flex justify-between border-t border-border pt-2 text-base">
                  <span className="font-extrabold text-foreground">Total</span>
                  <span className="font-extrabold text-foreground">
                    {formatNgn(merchSubtotal)}
                  </span>
                </div>
              )}
            </section>

            {accountEmailNeedsPaystackOverride && total > 0 ? (
              <Input
                label="Payment email"
                type="email"
                value={paymentEmail}
                onChange={(e) => setPaymentEmail(e.target.value)}
                hint="Your account email cannot be used with Paystack — enter a standard inbox for this payment."
              />
            ) : null}

            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Button
                size="lg"
                disabled={submitting || selectedMerch.length === 0}
                onClick={() => void onPay()}
              >
                {submitting ? "Processing…" : `Pay ${formatNgn(total)}`}
              </Button>
              <Link href={`/merch/hosts/${hostSlug}`}>
                <Button size="lg" variant="secondary">
                  Back to shop
                </Button>
              </Link>
            </div>

            <CheckoutTrustStrip />
          </>
        )}
      </Container>
    </main>
  );
}
