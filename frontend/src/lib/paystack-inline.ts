/** Paystack Inline (popup iframe) — keeps buyer on Pàdéyá checkout. */

const PAYSTACK_INLINE_SRC = "https://js.paystack.co/v1/inline.js";

type PaystackCallbackResponse = {
  reference?: string;
  status?: string;
};

type PaystackHandler = {
  openIframe: () => void;
};

type PaystackPopGlobal = {
  setup: (options: Record<string, unknown>) => PaystackHandler;
};

declare global {
  interface Window {
    PaystackPop?: PaystackPopGlobal;
  }
}

let scriptPromise: Promise<void> | null = null;

function loadPaystackInlineScript(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Paystack inline is browser-only"));
  }
  if (window.PaystackPop) return Promise.resolve();
  if (scriptPromise) return scriptPromise;

  scriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${PAYSTACK_INLINE_SRC}"]`,
    );
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener(
        "error",
        () => reject(new Error("Failed to load Paystack")),
        { once: true },
      );
      if (window.PaystackPop) resolve();
      return;
    }

    const script = document.createElement("script");
    script.src = PAYSTACK_INLINE_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Paystack"));
    document.body.appendChild(script);
  });

  return scriptPromise;
}

export type OpenPaystackPopupInput = {
  accessCode?: string | null;
  publicKey: string;
  email: string;
  amountKobo: number;
  reference: string;
};

export type PaystackPopupOutcome = "success" | "cancelled";

/**
 * Open Paystack payment in an overlay iframe.
 * Public key is required by Paystack Inline even when using server `access_code`.
 */
export async function openPaystackPopup(
  input: OpenPaystackPopupInput,
): Promise<PaystackPopupOutcome> {
  const publicKey = input.publicKey.trim();
  if (!publicKey.startsWith("pk_test_") && !publicKey.startsWith("pk_live_")) {
    throw new Error("Paystack public key is not configured");
  }

  await loadPaystackInlineScript();
  const PaystackPop = window.PaystackPop;
  if (!PaystackPop) {
    throw new Error("Paystack inline is unavailable");
  }

  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (outcome: PaystackPopupOutcome) => {
      if (settled) return;
      settled = true;
      resolve(outcome);
    };

    const email = input.email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      reject(new Error("A valid payment email is required"));
      return;
    }

    const amountKobo = Math.round(Number(input.amountKobo));
    if (!Number.isFinite(amountKobo) || amountKobo <= 0) {
      reject(new Error("Payment amount is invalid"));
      return;
    }

    const options: Record<string, unknown> = {
      key: publicKey,
      email,
      amount: amountKobo,
      ref: input.reference,
      currency: "NGN",
      onClose: () => finish("cancelled"),
      callback: (response: PaystackCallbackResponse) => {
        if (response?.reference) finish("success");
        else finish("cancelled");
      },
    };

    if (input.accessCode?.trim()) {
      options.access_code = input.accessCode.trim();
    }

    try {
      PaystackPop.setup(options).openIframe();
    } catch (err) {
      reject(err instanceof Error ? err : new Error("Paystack popup failed"));
    }
  });
}
