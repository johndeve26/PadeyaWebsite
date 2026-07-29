"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { CheckoutAttendeeDetails } from "@/components/checkout/CheckoutAttendeeDetails";
import { CheckoutPurchaseMode } from "@/components/checkout/CheckoutPurchaseMode";
import { CheckoutStepper } from "@/components/checkout/CheckoutStepper";
import { CheckoutTicketSelector } from "@/components/checkout/CheckoutTicketSelector";
import { CheckoutTrustStrip } from "@/components/checkout/CheckoutTrustStrip";
import {
  buildAttendeeSlots,
  CHECKOUT_STEPS,
  type AttendeeDraft,
  type CheckoutStepId,
  type GiftDelivery,
  type PurchaseMode,
  validateAttendeeDrafts,
} from "@/components/checkout/types";
import {
  answersToPayload,
  CheckoutQuestionsFields,
  validateCheckoutAnswers,
  type CheckoutAnswerErrors,
  type CheckoutAnswerMap,
} from "@/components/events/CheckoutQuestionsFields";
import { CheckoutBundlePicker } from "@/components/merch/CheckoutBundlePicker";
import { CheckoutMerchAddons } from "@/components/merch/CheckoutMerchAddons";
import {
  emptyShippingAddress,
  isShippingAddressComplete,
  ShippingAddressForm,
  shippingAddressToApiPayload,
  type ShippingAddressValues,
} from "@/components/merch/ShippingAddressForm";
import { RestrictedActionNotice } from "@/components/account/RestrictedActionNotice";
import {
  Alert,
  Badge,
  Button,
  Container,
  EmptyState,
  Input,
  Media,
  Radio,
  SkeletonLoader,
} from "@/components/ui";
import { useHostAffiliation } from "@/hooks/useHostAffiliation";
import { useUserRestrictions } from "@/hooks/useUserRestrictions";
import { ApiError } from "@/lib/api";
import {
  trackCheckoutAbandoned,
  trackCheckoutPageView,
  trackCheckoutPaymentStarted,
  trackMerchAddedToCheckout,
  trackMerchCheckoutStarted,
  trackMerchRemovedFromCheckout,
  trackPromoCodeEntered,
  trackPromoCodeResult,
  trackTicketTypeSelected,
} from "@/lib/analytics";
import { formatDateTime, formatNgn } from "@/lib/format";
import { formatPublicVenueDetail } from "@/lib/event-privacy";
import { checkoutOrder, checkCheckoutBuyerEmail, confirmCheckoutPayment, createOrder, fetchPaystackConfig, isPaystackCompatibleEmail, quoteBuyerFees, CHECKOUT_BUYER_EMAIL_KEY } from "@/lib/commerce-api";
import { openPaystackPopup } from "@/lib/paystack-inline";
import type { BuyerFeeQuote } from "@/lib/types/commerce";
import { fetchPublicEvent } from "@/lib/events-api";
import { readMerchDraftCart } from "@/lib/merch-draft-cart";
import {
  fetchEventBundles,
  fetchMerchCatalog,
  validateMerchDiscount,
} from "@/lib/merch-api";
import { variantAvailable } from "@/lib/merch-stock";
import { cartRequiresSignInForMerch } from "@/lib/merch-checkout-access";
import {
  captureAmbassadorReferral,
  formatAmbassadorCodeDisplay,
  readAmbassadorCodeFromSearchParams,
  resolveCheckoutReferral,
} from "@/lib/ambassador-referral";
import { validatePromo } from "@/lib/promos-api";
import { trackAmbassadorReferralLanding } from "@/lib/referral-click-track";
import type { EventItem, TicketType } from "@/lib/types/events";
import type {
  MerchBundle,
  MerchCatalogProduct,
  MerchVariant,
} from "@/lib/types/merch";

function checkoutReturnPath(slug: string, params: URLSearchParams): string {
  const qs = new URLSearchParams();
  for (const key of ["ref", "amb", "merch", "variant", "qty"] as const) {
    const value = params.get(key);
    if (value) qs.set(key, value);
  }
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return `/events/${slug}/checkout${suffix}`;
}

function checkoutLoginHref(slug: string, params: URLSearchParams): string {
  return `/login?next=${encodeURIComponent(checkoutReturnPath(slug, params))}`;
}

export default function CheckoutPage() {
  const params = useParams<{ slug: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, loading } = useAuth();
  const { hasAny } = useUserRestrictions();
  const checkoutBlocked = hasAny([
    "cannot_checkout",
    "cannot_buy_tickets",
    "cannot_buy_merch",
  ]);
  const [event, setEvent] = useState<EventItem | null>(null);
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [merchCatalog, setMerchCatalog] = useState<MerchCatalogProduct[]>([]);
  const [merchQuantities, setMerchQuantities] = useState<Record<string, number>>(
    {},
  );
  const [bundles, setBundles] = useState<MerchBundle[]>([]);
  const [bundleQuantities, setBundleQuantities] = useState<
    Record<string, number>
  >({});
  const [promoCode, setPromoCode] = useState("");
  const [promoNote, setPromoNote] = useState<string | null>(null);
  const [discountPreview, setDiscountPreview] = useState(0);
  const [merchDiscountCode, setMerchDiscountCode] = useState("");
  const [merchDiscountNote, setMerchDiscountNote] = useState<string | null>(
    null,
  );
  const [merchDiscountPreview, setMerchDiscountPreview] = useState(0);
  const [merchShippingPreview, setMerchShippingPreview] = useState<
    number | null
  >(null);
  const [feeQuote, setFeeQuote] = useState<BuyerFeeQuote | null>(null);
  const [checkoutAnswers, setCheckoutAnswers] = useState<CheckoutAnswerMap>({});
  const [answerErrors, setAnswerErrors] = useState<CheckoutAnswerErrors>({});
  const [fulfillmentMethod, setFulfillmentMethod] = useState<
    "pickup" | "shipping"
  >("pickup");
  const [shippingAddress, setShippingAddress] = useState<ShippingAddressValues>(
    emptyShippingAddress,
  );
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [paystackMode, setPaystackMode] = useState<"test" | "live" | null>(
    null,
  );
  const [paystackPublicKey, setPaystackPublicKey] = useState<string | null>(
    null,
  );
  const [step, setStep] = useState<CheckoutStepId>("tickets");
  const [codesOpen, setCodesOpen] = useState(false);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [purchaseMode, setPurchaseMode] = useState<PurchaseMode>("self");
  const [selfName, setSelfName] = useState("");
  const [selfEmail, setSelfEmail] = useState("");
  const [paymentEmail, setPaymentEmail] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [useSameForAll, setUseSameForAll] = useState(true);
  const [attendeeEdits, setAttendeeEdits] = useState<
    Record<string, Partial<AttendeeDraft>>
  >({});
  const [gift, setGift] = useState<GiftDelivery>({
    send_ticket_to_recipient: true,
    keep_buyer_copy: true,
    gift_message: "",
  });
  /** Explicit opt-in removed — logged-out checkout always uses buyer email. */
  const paymentStartedRef = useRef(false);
  const urlReferralCode = readAmbassadorCodeFromSearchParams(searchParams);
  const [explicitAmbassadorCode, setExplicitAmbassadorCode] = useState("");
  const prefillMerchId = (searchParams.get("merch") || "").trim();
  const prefillVariantId = (searchParams.get("variant") || "").trim();
  const prefillQty = Math.max(
    1,
    Number.parseInt(searchParams.get("qty") || "1", 10) || 1,
  );
  const fromMerchCart = searchParams.get("from_merch_cart") === "1";
  const { affiliated: isOwnHost } = useHostAffiliation({
    hostId: event?.host_id,
    hostSlug: event?.host_slug,
  });

  const effectiveSelfName = selfName || user?.full_name || "";
  const effectiveSelfEmail = selfEmail || user?.email || "";
  const accountEmailNeedsPaystackOverride = Boolean(
    user?.email && !isPaystackCompatibleEmail(user.email),
  );
  const paystackCustomerEmail = accountEmailNeedsPaystackOverride
    ? paymentEmail.trim()
    : effectiveSelfEmail.trim();

  useEffect(() => {
    void fetchPublicEvent(params.slug)
      .then((item) => {
        setEvent(item);
        const initial: Record<string, number> = {};
        for (const ticket of item.ticket_types ?? []) {
          if (ticket.visibility === "public" && ticket.status === "active") {
            initial[ticket.id] = 0;
          }
        }
        setQuantities(initial);
        void fetchEventBundles(item.id)
          .then((rows) => {
            setBundles(rows);
            const bq: Record<string, number> = {};
            for (const bundle of rows) bq[bundle.id] = 0;
            setBundleQuantities(bq);
          })
          .catch(() => {
            setBundles([]);
            setBundleQuantities({});
          });
        void fetchMerchCatalog(item.id, { authenticated: Boolean(user) })
          .then((rows) => {
            setMerchCatalog(rows);
            const mq: Record<string, number> = {};
            for (const product of rows) {
              for (const variant of product.variants) {
                mq[variant.id] = 0;
              }
            }
            const draft = fromMerchCart ? readMerchDraftCart(item.id) : null;
            if (draft && draft.lines.length > 0) {
              for (const line of draft.lines) {
                if (mq[line.variantId] === undefined) continue;
                const product = rows.find((p) =>
                  p.variants.some((v) => v.id === line.variantId),
                );
                const variant = product?.variants.find(
                  (v) => v.id === line.variantId,
                );
                if (!variant || !product) continue;
                mq[line.variantId] = Math.min(
                  line.quantity,
                  variantAvailable(variant),
                  product.max_per_order ??
                    product.max_per_buyer ??
                    line.quantity,
                );
              }
            } else if (prefillVariantId && mq[prefillVariantId] !== undefined) {
              const product = rows.find((p) =>
                p.variants.some((v) => v.id === prefillVariantId),
              );
              const variant = product?.variants.find(
                (v) => v.id === prefillVariantId,
              );
              if (variant) {
                const max = Math.min(
                  prefillQty,
                  variantAvailable(variant),
                  product?.max_per_order ??
                    product?.max_per_buyer ??
                    prefillQty,
                );
                mq[prefillVariantId] = Math.max(0, max);
              }
            } else if (prefillMerchId) {
              const product = rows.find((p) => p.id === prefillMerchId);
              const variant = product?.variants.find(
                (v) => variantAvailable(v) > 0,
              );
              if (variant && mq[variant.id] !== undefined) {
                mq[variant.id] = Math.min(
                  prefillQty,
                  variantAvailable(variant),
                  product?.max_per_order ??
                    product?.max_per_buyer ??
                    prefillQty,
                );
              }
            }
            setMerchQuantities(mq);
          })
          .catch(() => setMerchCatalog([]));
        trackCheckoutPageView({
          targetEventId: item.id,
          hostId: item.host_id,
        });
        if (urlReferralCode) {
          captureAmbassadorReferral(params.slug, urlReferralCode);
          captureAmbassadorReferral(item.id, urlReferralCode);
          trackAmbassadorReferralLanding({
            referral_code: urlReferralCode,
            event_id: item.id,
            landing_path: `/events/${params.slug}/checkout?ref=${urlReferralCode}`,
            source: "checkout",
          });
        }
      })
      .catch(() => setError("Event not available for checkout."));
  }, [
    params.slug,
    urlReferralCode,
    prefillMerchId,
    prefillVariantId,
    prefillQty,
    fromMerchCart,
  ]);

  useEffect(() => {
    if (!event?.id) return;
    void fetchMerchCatalog(event.id, { authenticated: Boolean(user) })
      .then(setMerchCatalog)
      .catch(() => undefined);
  }, [event?.id, user?.id]);

  useEffect(() => {
    let alive = true;
    void fetchPaystackConfig()
      .then((cfg) => {
        if (alive) {
          setPaystackMode(cfg.mode);
          setPaystackPublicKey(cfg.public_key ?? null);
        }
      })
      .catch(() => {
        if (alive) {
          setPaystackMode(null);
          setPaystackPublicKey(null);
        }
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!event) return;
    const onHide = () => {
      if (paymentStartedRef.current) return;
      if (document.visibilityState === "hidden") {
        trackCheckoutAbandoned({
          targetEventId: event.id,
          hostId: event.host_id,
        });
      }
    };
    const onPageHide = () => {
      if (paymentStartedRef.current) return;
      trackCheckoutAbandoned({
        targetEventId: event.id,
        hostId: event.host_id,
      });
    };
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("pagehide", onPageHide);
    return () => {
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("pagehide", onPageHide);
    };
  }, [event]);

  const selected = useMemo(() => {
    if (!event) return [] as { ticket: TicketType; quantity: number }[];
    return (event.ticket_types ?? [])
      .map((ticket) => ({ ticket, quantity: quantities[ticket.id] ?? 0 }))
      .filter((row) => row.quantity > 0);
  }, [event, quantities]);

  const attendees = useMemo(() => {
    const slots = buildAttendeeSlots(selected, {
      name: effectiveSelfName,
      email: effectiveSelfEmail,
    });
    return slots.map((slot) => {
      const key = `${slot.ticket_type_id}:${slot.unit_index}`;
      const edit = attendeeEdits[key];
      return edit ? { ...slot, ...edit } : slot;
    });
  }, [selected, effectiveSelfName, effectiveSelfEmail, attendeeEdits]);

  const selectedMerch = useMemo(() => {
    const rows: {
      product: MerchCatalogProduct;
      variant: MerchVariant;
      quantity: number;
    }[] = [];
    for (const product of merchCatalog) {
      for (const variant of product.variants) {
        const quantity = merchQuantities[variant.id] ?? 0;
        if (quantity > 0) {
          rows.push({ product, variant, quantity });
        }
      }
    }
    return rows;
  }, [merchCatalog, merchQuantities]);

  const selectedBundles = useMemo(() => {
    return bundles
      .map((bundle) => ({
        bundle,
        quantity: bundleQuantities[bundle.id] ?? 0,
      }))
      .filter((row) => row.quantity > 0);
  }, [bundles, bundleQuantities]);

  const ticketCount = selected.reduce((n, r) => n + r.quantity, 0);
  const merchCount = selectedMerch.reduce((n, r) => n + r.quantity, 0);
  const bundleCount = selectedBundles.reduce((n, r) => n + r.quantity, 0);
  const cartCount = ticketCount + merchCount + bundleCount;
  const allowMerchOnly = Boolean(event?.allow_merch_only_checkout);
  const merchNeedsTicketHint =
    merchCount > 0 &&
    ticketCount === 0 &&
    bundleCount === 0 &&
    !allowMerchOnly;
  const hasMerchLines = merchCount > 0 || bundleCount > 0;
  const signInRequiredForMerch = useMemo(
    () =>
      !user &&
      cartRequiresSignInForMerch({
        catalog: merchCatalog,
        selectedMerch,
        selectedBundles,
      }),
    [user, merchCatalog, selectedMerch, selectedBundles],
  );

  useEffect(() => {
    if (!signInRequiredForMerch) return;
    setError((prev) =>
      prev &&
      /sign in to unlock vault-exclusive|vault-exclusive merch in your cart/i.test(
        prev,
      )
        ? null
        : prev,
    );
  }, [signInRequiredForMerch]);
  const merchPickupAvailable =
    hasMerchLines &&
    (bundleCount > 0 ||
      selectedMerch.some((row) => row.product.pickup_enabled !== false));
  const merchShippingAvailable =
    merchCount > 0 &&
    selectedMerch.some((row) => Boolean(row.product.shipping_enabled));
  const showFulfillmentPicker =
    hasMerchLines && (merchPickupAvailable || merchShippingAvailable);
  const effectiveFulfillment: "pickup" | "shipping" | null = !hasMerchLines
    ? null
    : merchShippingAvailable && !merchPickupAvailable
      ? "shipping"
      : merchPickupAvailable && !merchShippingAvailable
        ? "pickup"
        : fulfillmentMethod;
  const needsShippingAddress = effectiveFulfillment === "shipping";
  const ticketsSubtotal = selected.reduce(
    (sum, row) => sum + Number(row.ticket.price) * row.quantity,
    0,
  );
  const merchSubtotal = selectedMerch.reduce(
    (sum, row) => sum + Number(row.variant.effective_price) * row.quantity,
    0,
  );
  const bundlesSubtotal = selectedBundles.reduce(
    (sum, row) => sum + Number(row.bundle.bundle_price) * row.quantity,
    0,
  );
  const subtotal = ticketsSubtotal + merchSubtotal + bundlesSubtotal;
  const shippingPreview =
    needsShippingAddress && merchShippingPreview != null
      ? merchShippingPreview
      : 0;
  const buyerFeePreview = Number(feeQuote?.buyer_fee_total ?? 0);
  const total = feeQuote
    ? Number(feeQuote.final_total)
    : Math.max(
        0,
        subtotal - discountPreview - merchDiscountPreview + shippingPreview,
      );

  useEffect(() => {
    let active = true;
    const handle = window.setTimeout(() => {
      void (async () => {
        if (
          !event?.host_id ||
          (subtotal <= 0 && discountPreview <= 0 && merchDiscountPreview <= 0)
        ) {
          if (active) setFeeQuote(null);
          return;
        }
        try {
          const quote = await quoteBuyerFees({
            host_id: event.host_id,
            ticket_subtotal: ticketsSubtotal + bundlesSubtotal,
            merch_subtotal: merchSubtotal,
            ticket_discount: discountPreview,
            merch_discount: merchDiscountPreview,
            shipping_amount: shippingPreview,
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
  }, [
    event?.host_id,
    ticketsSubtotal,
    merchSubtotal,
    bundlesSubtotal,
    discountPreview,
    merchDiscountPreview,
    shippingPreview,
    subtotal,
  ]);

  const publicTickets = (event?.ticket_types ?? []).filter(
    (t) => t.visibility === "public" && t.status === "active",
  );
  const checkoutQuestions = useMemo(
    () =>
      [...(event?.checkout_questions ?? [])].filter(
        (q): q is typeof q & { id: string } => Boolean(q.id),
      ),
    [event?.checkout_questions],
  );
  const answersValidation = useMemo(
    () => validateCheckoutAnswers(checkoutQuestions, checkoutAnswers),
    [checkoutQuestions, checkoutAnswers],
  );
  const answersReady =
    checkoutQuestions.length === 0 || !answersValidation.summary;

  const stepIndex = CHECKOUT_STEPS.findIndex((s) => s.id === step);
  const completedSteps = useMemo(() => {
    const set = new Set<CheckoutStepId>();
    if (cartCount > 0) set.add("tickets");
    if (ticketCount === 0 || purchaseMode) set.add("attendees");
    if (answersReady) set.add("details");
    return set;
  }, [cartCount, ticketCount, purchaseMode, answersReady]);

  async function onApplyPromo() {
    if (!event || !promoCode.trim() || selected.length === 0) return;
    setPromoNote(null);
    trackPromoCodeEntered({
      targetEventId: event.id,
      hostId: event.host_id,
      promoCode: promoCode.trim(),
    });
    try {
      const result = await validatePromo({
        code: promoCode.trim(),
        event_id: event.id,
        items: selected.map((row) => ({
          ticket_type_id: row.ticket.id,
          quantity: row.quantity,
        })),
      });
      if (!result.valid) {
        setDiscountPreview(0);
        setPromoNote(result.reason || "Invalid promo code");
        trackPromoCodeResult({
          targetEventId: event.id,
          hostId: event.host_id,
          promoCode: promoCode.trim(),
          success: false,
          reason: result.reason || "invalid",
        });
        return;
      }
      setDiscountPreview(Number(result.discount_amount));
      setPromoNote(
        `Promo ${result.code} applied (−${formatNgn(result.discount_amount)})`,
      );
      trackPromoCodeResult({
        targetEventId: event.id,
        hostId: event.host_id,
        promoCode: result.code ?? promoCode.trim(),
        success: true,
      });
    } catch (err) {
      setDiscountPreview(0);
      setPromoNote(err instanceof ApiError ? err.detail : "Could not validate promo");
      trackPromoCodeResult({
        targetEventId: event.id,
        hostId: event.host_id,
        promoCode: promoCode.trim(),
        success: false,
        reason: err instanceof ApiError ? err.detail || "error" : "error",
      });
    }
  }

  async function onApplyMerchDiscount() {
    if (!event || !merchDiscountCode.trim() || !hasMerchLines) return;
    setMerchDiscountNote(null);
    try {
      const items = [
        ...selectedMerch.map((row) => ({
          merch_variant_id: row.variant.id,
          quantity: row.quantity,
        })),
        ...selected.map((row) => ({
          ticket_type_id: row.ticket.id,
          quantity: row.quantity,
        })),
      ];
      const shippingProbe = needsShippingAddress ? 1000 : 0;
      const result = await validateMerchDiscount({
        code: merchDiscountCode.trim(),
        event_id: event.id,
        items,
        shipping_amount: shippingProbe,
      });
      if (!result.valid) {
        setMerchDiscountPreview(0);
        setMerchShippingPreview(null);
        setMerchDiscountNote(result.reason || "Invalid merch discount code");
        return;
      }
      const amount = Number(result.discount_amount);
      setMerchDiscountPreview(amount);
      setMerchShippingPreview(
        result.discount_type === "free_shipping"
          ? Number(result.shipping_amount)
          : null,
      );
      if (result.discount_type === "free_shipping") {
        setMerchDiscountNote(
          `Merch code ${result.code} applied (free shipping at checkout)`,
        );
      } else {
        setMerchDiscountNote(
          `Merch code ${result.code} applied (−${formatNgn(amount)})`,
        );
      }
    } catch (err) {
      setMerchDiscountPreview(0);
      setMerchShippingPreview(null);
      setMerchDiscountNote(
        err instanceof ApiError
          ? err.detail
          : "Could not validate merch discount",
      );
    }
  }

  function validateCheckoutBuyerIdentity(): string | null {
    if (user || cartCount === 0) return null;
    if (!effectiveSelfName.trim() || effectiveSelfName.trim().length < 2) {
      return "Enter your full name for receipts and your dashboard.";
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(effectiveSelfEmail.trim())) {
      return "Enter a valid email — we’ll create your account after payment confirms.";
    }
    return null;
  }

  async function assertLoggedOutEmailAllowed(): Promise<boolean> {
    if (user || !event) return true;
    const buyerErr = validateCheckoutBuyerIdentity();
    if (buyerErr) {
      setError(buyerErr);
      return false;
    }
    try {
      const check = await checkCheckoutBuyerEmail({
        email: effectiveSelfEmail.trim(),
        event_id: event.id,
        has_tickets: ticketCount > 0,
        has_merch: hasMerchLines,
      });
      if (check.status === "existing_account") {
        setError(
          "This email already has a Pàdéyá account. Sign in to finish checkout.",
        );
        return false;
      }
      return true;
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not verify checkout email.",
      );
      return false;
    }
  }

  async function goNext() {
    setError(null);
    if (signInRequiredForMerch) {
      setError("Sign in to unlock Vault-exclusive merch in your cart.");
      return;
    }
    if (step === "tickets") {
      if (cartCount === 0) {
        setError("Select at least one ticket, bundle, or merch item.");
        return;
      }
      if (!(await assertLoggedOutEmailAllowed())) return;
      setStep(ticketCount > 0 ? "attendees" : "details");
      return;
    }
    if (step === "attendees") {
      const buyerErr = validateCheckoutBuyerIdentity();
      if (buyerErr) {
        setError(buyerErr);
        return;
      }
      if (!(await assertLoggedOutEmailAllowed())) return;
      if (ticketCount > 0) {
        const attendeeError = validateAttendeeDrafts(purchaseMode, attendees, {
          recipientName,
          recipientEmail,
          useSameForAll,
          selfName: effectiveSelfName,
          selfEmail: effectiveSelfEmail,
        });
        if (attendeeError) {
          setError(attendeeError);
          return;
        }
        if (
          purchaseMode !== "self" &&
          !gift.send_ticket_to_recipient &&
          !gift.keep_buyer_copy
        ) {
          setError("Choose Send ticket to recipient and/or Keep a buyer copy.");
          return;
        }
      }
      setStep("details");
      return;
    }
    if (step === "details") {
      const { errors: fieldErrors, summary } = validateCheckoutAnswers(
        checkoutQuestions,
        checkoutAnswers,
      );
      if (summary) {
        setAnswerErrors(fieldErrors);
        setError(summary);
        return;
      }
      if (needsShippingAddress && !isShippingAddressComplete(shippingAddress)) {
        setError("Enter a complete delivery address for shipping.");
        return;
      }
      const buyerErr = validateCheckoutBuyerIdentity();
      if (buyerErr) {
        setError(buyerErr);
        return;
      }
      if (!(await assertLoggedOutEmailAllowed())) return;
      setStep("review");
      return;
    }
  }

  async function onPay() {
    if (
      !event ||
      (selected.length === 0 &&
        selectedMerch.length === 0 &&
        selectedBundles.length === 0)
    ) {
      setError("Select at least one ticket, bundle, or merch item.");
      setStep("tickets");
      return;
    }
    if (signInRequiredForMerch) {
      setError("Sign in to unlock Vault-exclusive merch in your cart.");
      return;
    }
    if (!user) {
      if (!(await assertLoggedOutEmailAllowed())) {
        setStep(ticketCount > 0 ? "attendees" : "tickets");
        return;
      }
    }
    if (ticketCount > 0) {
      const attendeeError = validateAttendeeDrafts(purchaseMode, attendees, {
        recipientName,
        recipientEmail,
        useSameForAll,
        selfName: effectiveSelfName,
        selfEmail: effectiveSelfEmail,
      });
      if (attendeeError) {
        setError(attendeeError);
        setStep("attendees");
        return;
      }
    }
    const { errors: fieldErrors, summary } = validateCheckoutAnswers(
      checkoutQuestions,
      checkoutAnswers,
    );
    if (summary) {
      setAnswerErrors(fieldErrors);
      setError(summary);
      setStep("details");
      return;
    }
    if (needsShippingAddress && !isShippingAddressComplete(shippingAddress)) {
      setError("Enter a complete delivery address for shipping.");
      setStep("details");
      return;
    }
    if (accountEmailNeedsPaystackOverride && total > 0) {
      if (!paystackCustomerEmail) {
        setError(
          "Enter a payment email Paystack accepts (demo @*.test addresses won't work).",
        );
        setStep("review");
        return;
      }
      if (!isPaystackCompatibleEmail(paystackCustomerEmail)) {
        setError(
          "Use a standard email for payment (for example Gmail or work email). Demo @*.test addresses are not accepted by Paystack.",
        );
        setStep("review");
        return;
      }
    }
    setAnswerErrors({});
    setSubmitting(true);
    setError(null);
    try {
      const answerPayload =
        checkoutQuestions.length > 0
          ? answersToPayload(checkoutAnswers)
          : [];

      const purchasePayload =
        ticketCount === 0
          ? {}
          : purchaseMode === "self"
            ? {
                purchase_mode: "self" as const,
                attendee_name: effectiveSelfName.trim(),
                attendee_email: effectiveSelfEmail.trim(),
              }
            : purchaseMode === "other"
              ? {
                  purchase_mode: "other" as const,
                  recipient_name: recipientName.trim(),
                  recipient_email: recipientEmail.trim(),
                  gift_message: gift.gift_message.trim() || undefined,
                  send_ticket_to_recipient: gift.send_ticket_to_recipient,
                  keep_buyer_copy: gift.keep_buyer_copy,
                }
              : {
                  purchase_mode: "group" as const,
                  use_same_buyer_details_for_all: useSameForAll,
                  attendee_name: useSameForAll
                    ? effectiveSelfName.trim()
                    : undefined,
                  attendee_email: useSameForAll
                    ? effectiveSelfEmail.trim()
                    : undefined,
                  send_ticket_to_recipient: gift.send_ticket_to_recipient,
                  keep_buyer_copy: gift.keep_buyer_copy,
                  gift_message: gift.gift_message.trim() || undefined,
                  attendees: useSameForAll
                    ? undefined
                    : attendees.map((a) => ({
                        ticket_type_id: a.ticket_type_id,
                        unit_index: a.unit_index,
                        attendee_name: a.attendee_name.trim(),
                        attendee_email: a.attendee_email.trim(),
                        attendee_phone: a.attendee_phone.trim() || undefined,
                      })),
                };

      const orderBody = {
        event_id: event.id,
        items: [
          ...selectedBundles.map((row) => ({
            item_kind: "bundle" as const,
            bundle_id: row.bundle.id,
            quantity: row.quantity,
          })),
          ...selected.map((row) => ({
            item_kind: "ticket" as const,
            ticket_type_id: row.ticket.id,
            quantity: row.quantity,
          })),
          ...selectedMerch.map((row) => ({
            item_kind: "merch" as const,
            merch_variant_id: row.variant.id,
            quantity: row.quantity,
          })),
        ],
        promo_code:
          selected.length > 0 || selectedBundles.length > 0
            ? promoCode.trim() || undefined
            : undefined,
        merch_discount_code: hasMerchLines
          ? merchDiscountCode.trim() || undefined
          : undefined,
        ...(() => {
          const attributed = resolveCheckoutReferral({
            eventKey: event.id,
            urlCode: urlReferralCode,
            explicitCode: explicitAmbassadorCode,
          });
          return attributed.code
            ? {
                referral_code: attributed.code,
                referral_source: attributed.source ?? undefined,
              }
            : {};
        })(),
        ...(hasMerchLines && effectiveFulfillment
          ? { fulfillment_method: effectiveFulfillment }
          : {}),
        ...(needsShippingAddress
          ? { shipping_address: shippingAddressToApiPayload(shippingAddress) }
          : {}),
        ...(answerPayload.length > 0
          ? { checkout_answers: answerPayload }
          : {}),
        ...purchasePayload,
        ...(!user
          ? {
              guest_buyer_name: effectiveSelfName.trim(),
              guest_buyer_email: effectiveSelfEmail.trim(),
            }
          : {}),
      };
      // Never issue tickets here — free completion / Paystack webhook do that server-side.
      const order = await createOrder(orderBody);
      paymentStartedRef.current = true;
      trackCheckoutPaymentStarted({
        targetEventId: event.id,
        hostId: event.host_id,
        orderId: order.id,
      });
      if (merchCount > 0 || bundleCount > 0) {
        trackMerchCheckoutStarted({
          targetEventId: event.id,
          hostId: event.host_id,
          orderId: order.id,
          merchItemCount: merchCount + bundleCount,
        });
      }
      const checkout = await checkoutOrder(
        order.id,
        accountEmailNeedsPaystackOverride && total > 0
          ? { payment_email: paystackCustomerEmail }
          : undefined,
      );
      if (checkout.free_checkout) {
        if (user) {
          router.push(`/dashboard/orders/${order.id}`);
        } else {
          try {
            sessionStorage.setItem(
              CHECKOUT_BUYER_EMAIL_KEY,
              effectiveSelfEmail.trim().toLowerCase(),
            );
          } catch {
            /* ignore */
          }
          router.push(
            `/checkout/success?order=${encodeURIComponent(order.reference)}`,
          );
        }
        return;
      }
      const paystackEmail = (
        checkout.paystack_customer_email ||
        (accountEmailNeedsPaystackOverride
          ? paystackCustomerEmail
          : !user
            ? effectiveSelfEmail.trim()
            : user?.email || effectiveSelfEmail.trim())
      )
        .trim()
        .toLowerCase();

      if (!isPaystackCompatibleEmail(paystackEmail)) {
        setError(
          accountEmailNeedsPaystackOverride
            ? "Enter a standard payment email on the review step (demo @*.test addresses are not accepted by Paystack)."
            : "Use a standard email for payment (for example Gmail or work email).",
        );
        paymentStartedRef.current = false;
        setStep(accountEmailNeedsPaystackOverride ? "review" : "attendees");
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
      const publicKey =
        (checkout.public_key || paystackPublicKey || "").trim();
      if (checkout.access_code || publicKey) {
        if (!publicKey) {
          setError(
            "Paystack public key is missing. Set it in Admin → Payment integration.",
          );
          paymentStartedRef.current = false;
          return;
        }
        try {
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
              // Webhook may still confirm; receipt page retries verify.
            }
            try {
              sessionStorage.setItem(
                CHECKOUT_BUYER_EMAIL_KEY,
                (user?.email || effectiveSelfEmail).trim().toLowerCase(),
              );
            } catch {
              /* ignore */
            }
            router.push(
              `/checkout/success?order=${encodeURIComponent(checkout.reference)}`,
            );
            return;
          }
          setError("Payment was cancelled. You can try again when ready.");
          paymentStartedRef.current = false;
          return;
        } catch {
          if (checkout.authorization_url) {
            window.location.href = checkout.authorization_url;
            return;
          }
        }
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

  if (loading) {
    return (
      <main className="bg-background py-16">
        <Container width="narrow">
          <SkeletonLoader lines={6} />
        </Container>
      </main>
    );
  }

  if (!event) {
    return (
      <main className="bg-background py-16">
        <Container width="narrow">
          {error ? (
            <EmptyState
              title="Checkout unavailable"
              description={error}
              action={
                <Link href="/events">
                  <Button variant="primary">Browse events</Button>
                </Link>
              }
            />
          ) : (
            <SkeletonLoader lines={6} />
          )}
        </Container>
      </main>
    );
  }

  if (checkoutBlocked) {
    return (
      <main className="bg-background py-16">
        <Container width="narrow" className="space-y-4">
          <RestrictedActionNotice />
          <Link href={`/events/${event.slug}`}>
            <Button variant="secondary">Back to event</Button>
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
            title="This is your event"
            description="You can’t buy tickets or merch from your own host workspace."
            action={
              <Link href={`/host/events/${event.id}`}>
                <Button>Manage event</Button>
              </Link>
            }
          />
        </Container>
      </main>
    );
  }

  const when = formatDateTime(event.start_datetime);
  const modeLabel =
    purchaseMode === "self"
      ? "Myself"
      : purchaseMode === "other"
        ? "Someone else"
        : "Group";

  const showCheckoutBuyerFields =
    !user && cartCount > 0 && !signInRequiredForMerch;

  const checkoutBuyerFields = showCheckoutBuyerFields ? (
    <div className="space-y-3 rounded-[var(--radius-md)] border border-border bg-muted/30 p-3 sm:p-4">
      <Input
        label="Full name"
        value={effectiveSelfName}
        onChange={(e) => setSelfName(e.target.value)}
        autoComplete="name"
      />
      <Input
        label="Email for receipts & your dashboard"
        type="email"
        value={effectiveSelfEmail}
        onChange={(e) => setSelfEmail(e.target.value)}
        autoComplete="email"
      />
      <Link
        href={checkoutLoginHref(params.slug, searchParams)}
        className="inline-block text-sm font-semibold text-foreground underline-offset-2 hover:underline"
      >
        Already have an account? Sign in
      </Link>
    </div>
  ) : null;

  const summaryBody = (
    <div className="space-y-4">
      <h2 className="text-lg font-extrabold tracking-tight text-foreground">
        Order summary
      </h2>
      {cartCount === 0 ? (
        <>
          <p className="text-sm text-muted-foreground">
            Select tickets or merch to continue.
          </p>
          <CheckoutTrustStrip />
        </>
      ) : (
        <>
        <ul className="space-y-2.5 border-b border-border pb-3">
          {selectedBundles.map((row) => (
            <li
              key={row.bundle.id}
              className="flex justify-between gap-3 text-sm"
            >
              <span className="text-muted-foreground">
                {row.quantity} × {row.bundle.name}
              </span>
              <span className="font-bold tabular-nums text-foreground">
                {formatNgn(Number(row.bundle.bundle_price) * row.quantity)}
              </span>
            </li>
          ))}
          {selected.map((row) => (
            <li
              key={row.ticket.id}
              className="flex justify-between gap-3 text-sm"
            >
              <span className="text-muted-foreground">
                {row.quantity} × {row.ticket.name}
              </span>
              <span className="font-bold tabular-nums text-foreground">
                {formatNgn(Number(row.ticket.price) * row.quantity)}
              </span>
            </li>
          ))}
          {selectedMerch.map((row) => (
            <li
              key={row.variant.id}
              className="flex justify-between gap-3 text-sm"
            >
              <span className="text-muted-foreground">
                {row.quantity} × {row.product.name}
                {row.variant.label ? ` (${row.variant.label})` : ""}
              </span>
              <span className="font-bold tabular-nums text-foreground">
                {formatNgn(Number(row.variant.effective_price) * row.quantity)}
              </span>
            </li>
          ))}
          {ticketCount > 0 ? (
            <li className="text-xs text-muted-foreground">For: {modeLabel}</li>
          ) : null}
        </ul>

      <button
        type="button"
        className="flex w-full items-center justify-between text-sm font-semibold text-foreground"
        onClick={() => setCodesOpen((v) => !v)}
      >
        Promo &amp; ambassador
        <span className="text-muted-foreground">{codesOpen ? "−" : "+"}</span>
      </button>
      {codesOpen ? (
        <div className="space-y-3">
          <div className="space-y-2">
            <Input
              label="Promo code"
              hint="Ticket promo — separate from merch discounts"
              value={promoCode}
              onChange={(e) => {
                setPromoCode(e.target.value);
                setDiscountPreview(0);
                setPromoNote(null);
              }}
              placeholder="SAVE10"
            />
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={!promoCode.trim() || selected.length === 0}
              onClick={() => void onApplyPromo()}
            >
              Apply promo
            </Button>
            {promoNote ? (
              <p
                className={
                  discountPreview > 0
                    ? "text-sm font-medium text-success"
                    : "text-sm text-muted-foreground"
                }
              >
                {promoNote}
              </p>
            ) : null}
          </div>
          <Input
            label="Ambassador code"
            hint="Optional. An explicit code here wins over a referral link or cookie."
            value={explicitAmbassadorCode}
            onChange={(e) => setExplicitAmbassadorCode(e.target.value)}
            placeholder="TOLUAFRO"
          />
          {hasMerchLines ? (
            <div className="space-y-2">
              <Input
                label="Merch discount code"
                hint="Merch-only codes — not ticket promos"
                value={merchDiscountCode}
                onChange={(e) => {
                  setMerchDiscountCode(e.target.value);
                  setMerchDiscountPreview(0);
                  setMerchShippingPreview(null);
                  setMerchDiscountNote(null);
                }}
                placeholder="MERCH10"
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={!merchDiscountCode.trim()}
                onClick={() => void onApplyMerchDiscount()}
              >
                Apply merch code
              </Button>
              {merchDiscountNote ? (
                <p
                  className={
                    merchDiscountPreview > 0 ||
                    (merchShippingPreview !== null &&
                      merchDiscountNote.toLowerCase().includes("free shipping"))
                      ? "text-sm font-medium text-success"
                      : "text-sm text-muted-foreground"
                  }
                >
                  {merchDiscountNote}
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="space-y-1.5 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Subtotal</span>
          <span className="tabular-nums">{formatNgn(subtotal)}</span>
        </div>
        {discountPreview > 0 ? (
          <div className="flex justify-between text-success">
            <span>Ticket discount</span>
            <span className="tabular-nums">−{formatNgn(discountPreview)}</span>
          </div>
        ) : null}
        {merchDiscountPreview > 0 ? (
          <div className="flex justify-between text-success">
            <span>Merch discount</span>
            <span className="tabular-nums">
              −{formatNgn(merchDiscountPreview)}
            </span>
          </div>
        ) : null}
        {shippingPreview > 0 ? (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Shipping</span>
            <span className="tabular-nums">{formatNgn(shippingPreview)}</span>
          </div>
        ) : null}
        {(feeQuote?.fee_breakdown ?? []).map((line) => (
          <div key={line.fee_key} className="flex justify-between">
            <span className="text-muted-foreground">{line.label}</span>
            <span className="tabular-nums">
              {formatNgn(Number(line.amount))}
            </span>
          </div>
        ))}
        {buyerFeePreview > 0 && (feeQuote?.fee_breakdown?.length ?? 0) === 0 ? (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Service fee</span>
            <span className="tabular-nums">{formatNgn(buyerFeePreview)}</span>
          </div>
        ) : null}
        <div className="flex justify-between border-t border-border pt-2 text-base font-extrabold">
          <span>Total</span>
          <span className="tabular-nums">{formatNgn(total)}</span>
        </div>
      </div>

      {merchNeedsTicketHint ? (
        <Alert tone="warning" title="Ticket usually required">
          Merch-only checkout is off for this event. Add a ticket, or continue if
          you already hold one — the server will confirm.
        </Alert>
      ) : null}
      {error && !signInRequiredForMerch ? (
        <Alert tone="danger" title="Checkout error">
          {error}
        </Alert>
      ) : null}
      {!user ? (
        signInRequiredForMerch ? (
          <Alert
            tone="warning"
            title="Vault-exclusive merch"
            action={
              <Link href={checkoutLoginHref(params.slug, searchParams)}>
                <Button size="sm" variant="secondary">
                  Sign in
                </Button>
              </Link>
            }
          >
            Your cart includes Vault-exclusive items. Sign in and unlock Vault
            access for this host to finish checkout — email-only checkout
            doesn&apos;t apply here.
          </Alert>
        ) : (
        <Alert
          tone="info"
          title="Checkout email"
        >
          Enter your name and email below. After payment confirms, we&apos;ll
          open a dashboard account for this address and email you a link to set
          your password. Tickets and merch will appear there.{" "}
          <Link
            href={checkoutLoginHref(params.slug, searchParams)}
            className="font-semibold underline-offset-2 hover:underline"
          >
            Already have an account? Sign in
          </Link>
        </Alert>
        )
      ) : (
        <Alert tone="info" title="Your account">
          Checking out as{" "}
          <span className="font-semibold text-foreground">{user.email}</span>.
          Ticket details are prefilled from your profile.
          {accountEmailNeedsPaystackOverride ? (
            <>
              {" "}
              Demo-style emails are not accepted by Paystack — enter a payment
              email on the review step.
            </>
          ) : null}
        </Alert>
      )}

      {checkoutBuyerFields}

      {step === "review" ? (
        <Button
          className="hidden w-full lg:inline-flex"
          disabled={submitting || cartCount === 0 || signInRequiredForMerch}
          onClick={() => void onPay()}
        >
          {submitting
            ? "Starting checkout…"
            : total === 0
              ? "Complete free order"
              : "Pay securely"}
        </Button>
      ) : (
        <Button
          className="hidden w-full lg:inline-flex"
          disabled={
            submitting ||
            (step === "tickets" && cartCount === 0) ||
            signInRequiredForMerch
          }
          onClick={() => void goNext()}
        >
          Continue
        </Button>
      )}
      <CheckoutTrustStrip />
        </>
      )}
    </div>
  );

  return (
    <main className="min-w-0 overflow-x-clip bg-background py-6 pb-28 sm:py-10 lg:py-12 lg:pb-12">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-gradient-to-b from-muted/80 to-transparent" />
      <Container className="relative grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(280px,340px)] lg:gap-10">
        <div className="space-y-5">
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Pàdéyá checkout
            </p>
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
              Secure checkout
            </h1>
            <CheckoutStepper
              current={step}
              completed={completedSteps}
              onSelect={(id) => {
                const target = CHECKOUT_STEPS.findIndex((s) => s.id === id);
                if (target <= stepIndex) setStep(id);
              }}
            />
            {paystackMode === "test" ? (
              <Alert tone="info" title="Paystack test mode">
                Payments use Paystack test keys — no real charges. Use Paystack test
                cards from their docs. Switch to Live in Admin → System → Payment
                integration when you go production.
              </Alert>
            ) : null}
            {paystackMode === "live" ? (
              <Alert tone="warning" title="Live payments">
                Paystack is in live mode — real money will be charged.
              </Alert>
            ) : null}
          </div>

          {checkoutBuyerFields ? (
            <div className={summaryOpen ? "hidden" : "lg:hidden"}>
              {checkoutBuyerFields}
            </div>
          ) : null}

          <section className="overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card">
            <div className="grid sm:grid-cols-[140px_1fr]">
              <div className="relative min-h-[120px] bg-surface-dark">
                {event.banner_url ? (
                  <Media src={event.banner_url} />
                ) : (
                  <div className="padeya-hero-glow absolute inset-0" />
                )}
              </div>
              <div className="space-y-1.5 p-4 sm:p-5">
                {event.category ? (
                  <Badge tone="outline">{event.category.name}</Badge>
                ) : null}
                <h2 className="text-lg font-extrabold tracking-tight text-foreground">
                  {event.title}
                </h2>
                <p className="text-sm text-muted-foreground">{when}</p>
                <p className="text-sm text-muted-foreground">
                  {formatPublicVenueDetail(event)}
                </p>
                {urlReferralCode || explicitAmbassadorCode ? (
                  <p className="text-xs text-muted-foreground">
                    Ambassador @
                    {formatAmbassadorCodeDisplay(
                      explicitAmbassadorCode || urlReferralCode,
                    )}
                  </p>
                ) : null}
              </div>
            </div>
          </section>

          {step === "tickets" ? (
            <section className="space-y-5 rounded-[var(--radius-lg)] border border-border bg-card p-4 sm:p-5">
              {bundles.length > 0 ? (
                <CheckoutBundlePicker
                  bundles={bundles}
                  quantities={bundleQuantities}
                  onQuantityChange={(bundleId, quantity) => {
                    setBundleQuantities((prev) => ({
                      ...prev,
                      [bundleId]: quantity,
                    }));
                    setDiscountPreview(0);
                    setPromoNote(null);
                  }}
                />
              ) : null}
              <div className="space-y-3">
                <h3 className="text-base font-extrabold text-foreground">
                  Select tickets
                </h3>
                <CheckoutTicketSelector
                  tickets={publicTickets}
                  quantities={quantities}
                  onQuantityChange={(ticketId, nextQty, ticket) => {
                    const prevQty = quantities[ticketId] ?? 0;
                    setQuantities((prev) => ({
                      ...prev,
                      [ticketId]: nextQty,
                    }));
                    setDiscountPreview(0);
                    setPromoNote(null);
                    if (prevQty === 0 && nextQty > 0 && event) {
                      trackTicketTypeSelected({
                        targetEventId: event.id,
                        hostId: event.host_id,
                        ticketTypeId: ticket.id,
                        ticketTypeName: ticket.name,
                        ticketPrice: ticket.price,
                      });
                    }
                  }}
                />
              </div>
              {merchCatalog.length > 0 ? (
                <CheckoutMerchAddons
                  products={merchCatalog}
                  quantities={merchQuantities}
                  unlocked
                  allowMerchOnly={allowMerchOnly}
                  onQuantityChange={(variantId, quantity) => {
                    const product = merchCatalog.find((p) =>
                      p.variants.some((v) => v.id === variantId),
                    );
                    const prevQty = merchQuantities[variantId] ?? 0;
                    setMerchQuantities((prev) => ({
                      ...prev,
                      [variantId]: quantity,
                    }));
                    if (!event || !product) return;
                    if (prevQty === 0 && quantity > 0) {
                      trackMerchAddedToCheckout({
                        targetEventId: event.id,
                        hostId: event.host_id,
                        merchProductId: product.id,
                        merchVariantId: variantId,
                        quantity,
                      });
                    } else if (prevQty > 0 && quantity === 0) {
                      trackMerchRemovedFromCheckout({
                        targetEventId: event.id,
                        hostId: event.host_id,
                        merchProductId: product.id,
                        merchVariantId: variantId,
                      });
                    }
                  }}
                />
              ) : null}
            </section>
          ) : null}

          {step === "attendees" && ticketCount > 0 ? (
            <section className="space-y-5 rounded-[var(--radius-lg)] border border-border bg-card p-4 sm:p-5">
              {user ? (
                <div className="rounded-[var(--radius-md)] border border-border bg-muted/40 p-4">
                  <p className="text-sm font-bold text-foreground">
                    Your account
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Signed in as {user.email}. Details below are prefilled — edit
                    if entry should use a different name or email.
                  </p>
                </div>
              ) : null}
              <CheckoutPurchaseMode
                value={purchaseMode}
                onChange={setPurchaseMode}
                signedIn={Boolean(user)}
              />
              <CheckoutAttendeeDetails
                mode={purchaseMode}
                selfName={effectiveSelfName}
                selfEmail={effectiveSelfEmail}
                onSelfChange={(field, value) => {
                  if (field === "name") setSelfName(value);
                  if (field === "email") setSelfEmail(value);
                }}
                recipientName={recipientName}
                recipientEmail={recipientEmail}
                onRecipientChange={(field, value) => {
                  if (field === "name") setRecipientName(value);
                  if (field === "email") setRecipientEmail(value);
                }}
                gift={gift}
                onGiftChange={setGift}
                useSameForAll={useSameForAll}
                onUseSameForAll={setUseSameForAll}
                attendees={attendees}
                onAttendeeChange={(_index, next) => {
                  const key = `${next.ticket_type_id}:${next.unit_index}`;
                  setAttendeeEdits((prev) => ({
                    ...prev,
                    [key]: {
                      attendee_name: next.attendee_name,
                      attendee_email: next.attendee_email,
                      attendee_phone: next.attendee_phone,
                    },
                  }));
                }}
              />
            </section>
          ) : null}

          {step === "details" ? (
            <section className="space-y-5 rounded-[var(--radius-lg)] border border-border bg-card p-4 sm:p-5">
              {showFulfillmentPicker ? (
                <div id="checkout-fulfillment" className="space-y-4">
                  <h3 className="text-base font-extrabold text-foreground">
                    Merch fulfillment
                  </h3>
                  {merchPickupAvailable && merchShippingAvailable ? (
                    <div className="space-y-2">
                      <Radio
                        name="fulfillment_method"
                        value="pickup"
                        checked={fulfillmentMethod === "pickup"}
                        onChange={() => setFulfillmentMethod("pickup")}
                        label="Pickup at event"
                        hint="Show your merch pickup code at the stand."
                      />
                      <Radio
                        name="fulfillment_method"
                        value="shipping"
                        checked={fulfillmentMethod === "shipping"}
                        onChange={() => setFulfillmentMethod("shipping")}
                        label="Delivery"
                        hint="Address stays private on Pàdéyá — never shown publicly."
                      />
                    </div>
                  ) : null}
                  {needsShippingAddress ? (
                    <ShippingAddressForm
                      value={shippingAddress}
                      onChange={setShippingAddress}
                      disabled={submitting}
                    />
                  ) : null}
                </div>
              ) : null}
              {checkoutQuestions.length > 0 ? (
                <div id="checkout-questions">
                  <CheckoutQuestionsFields
                    questions={checkoutQuestions}
                    answers={checkoutAnswers}
                    errors={answerErrors}
                    onChange={(next) => {
                      setCheckoutAnswers(next);
                      if (Object.keys(answerErrors).length > 0) {
                        setAnswerErrors(
                          validateCheckoutAnswers(checkoutQuestions, next)
                            .errors,
                        );
                      }
                    }}
                  />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No host questions for this event. Continue to review your
                  order.
                </p>
              )}
            </section>
      ) : null}

      {step === "review" ? (
            <section className="space-y-4 rounded-[var(--radius-lg)] border border-border bg-card p-4 sm:p-5">
              <h3 className="text-base font-extrabold text-foreground">
                Review order
              </h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Event</dt>
                  <dd className="font-medium text-foreground">{event.title}</dd>
                </div>
                {ticketCount > 0 ? (
                  <div className="flex justify-between gap-3">
                    <dt className="text-muted-foreground">Purchase mode</dt>
                    <dd className="font-medium text-foreground">{modeLabel}</dd>
                  </div>
                ) : null}
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Items</dt>
                  <dd className="font-medium text-foreground">
                    {ticketCount ? `${ticketCount} ticket(s)` : null}
                    {ticketCount && (merchCount || bundleCount) ? " · " : null}
                    {merchCount || bundleCount
                      ? `${merchCount + bundleCount} merch`
                      : null}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Total (preview)</dt>
                  <dd className="font-extrabold tabular-nums text-foreground">
                    {formatNgn(total)}
                  </dd>
                </div>
              </dl>
              {accountEmailNeedsPaystackOverride && total > 0 ? (
                <Input
                  id="paystack-payment-email"
                  label="Payment email (Paystack)"
                  type="email"
                  autoComplete="email"
                  value={paymentEmail}
                  onChange={(e) => setPaymentEmail(e.target.value)}
                  hint="Your account uses a demo address. Paystack needs a standard email (e.g. Gmail) for receipts — tickets still stay on your account."
                  disabled={submitting}
                />
              ) : null}
            </section>
          ) : null}

          {error && step !== "review" ? (
            <Alert tone="danger" title="Check this step">
              {error}
            </Alert>
          ) : null}

          <div className="hidden gap-3 lg:flex">
            {stepIndex > 0 ? (
              <Button
                type="button"
                variant="secondary"
                onClick={() =>
                  setStep(CHECKOUT_STEPS[Math.max(0, stepIndex - 1)].id)
                }
              >
                Back
              </Button>
            ) : null}
            {step !== "review" ? (
              <Button type="button" onClick={goNext}>
                Continue
              </Button>
            ) : null}
          </div>
        </div>

        <aside className="hidden space-y-4 lg:sticky lg:top-24 lg:block lg:self-start">
          <div className="rounded-[var(--radius-lg)] border border-border bg-card p-5 shadow-[var(--shadow-soft)]">
            {summaryBody}
          </div>
        </aside>
      </Container>

      {/* Mobile sticky checkout bar */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur lg:hidden">
        <button
          type="button"
          className="mb-2 flex w-full items-center justify-between text-left text-xs text-muted-foreground"
          onClick={() => setSummaryOpen((v) => !v)}
        >
          <span>{summaryOpen ? "Hide summary" : "Show summary"}</span>
          <span className="font-extrabold tabular-nums text-foreground">
            {formatNgn(total)}
          </span>
        </button>
        {summaryOpen ? (
          <div className="mb-3 max-h-48 overflow-y-auto rounded-[var(--radius-md)] border border-border bg-background p-3">
            {summaryBody}
          </div>
        ) : null}
        <div className="mx-auto flex w-full max-w-lg min-w-0 items-center gap-3">
          {stepIndex > 0 ? (
            <Button
              type="button"
              variant="secondary"
              className="shrink-0"
              onClick={() =>
                setStep(CHECKOUT_STEPS[Math.max(0, stepIndex - 1)].id)
              }
            >
              Back
            </Button>
          ) : null}
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs text-muted-foreground">
              {cartCount
                ? [
                    ticketCount ? `${ticketCount} ticket(s)` : null,
                    merchCount ? `${merchCount} merch` : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")
                : "Select items"}
            </p>
            <p className="truncate text-lg font-extrabold tabular-nums text-foreground">
              {formatNgn(total)}
            </p>
          </div>
          {step === "review" ? (
            <Button
              className="shrink-0 whitespace-nowrap px-5"
              disabled={submitting || cartCount === 0 || signInRequiredForMerch}
              onClick={() => void onPay()}
            >
              {submitting ? "…" : total === 0 ? "Get free" : "Pay"}
            </Button>
          ) : (
            <Button
              className="shrink-0 whitespace-nowrap px-5"
              disabled={
                submitting ||
                (step === "tickets" && cartCount === 0) ||
                signInRequiredForMerch
              }
              onClick={() => void goNext()}
            >
              Continue
            </Button>
          )}
        </div>
      </div>
    </main>
  );
}
