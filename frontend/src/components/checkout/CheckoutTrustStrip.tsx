"use client";

import Link from "next/link";

export function CheckoutTrustStrip() {
  return (
    <div className="space-y-2 text-xs leading-relaxed text-muted-foreground">
      <p>Secure payment · Tickets &amp; QR only after payment confirmation</p>
      <p>
        Show your QR at entry.{" "}
        <Link href="/support" className="font-semibold text-foreground underline-offset-2 hover:underline">
          Refunds &amp; support
        </Link>
      </p>
    </div>
  );
}
