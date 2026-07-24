"use client";

import { QRCodeSVG } from "qrcode.react";

import { Badge } from "@/components/ui";

type Props = {
  pickupCode: string;
  qrToken?: string | null;
  qrTyp?: string | null;
  disabled?: boolean;
  offlineHint?: string | null;
};

/**
 * Merch pickup QR — typ=padeya.merch.pickup (not ticket check-in QR).
 * Token is display-only after paid; desk scan verifies server-side.
 */
export function MerchPickupQr({
  pickupCode,
  qrToken,
  qrTyp = "padeya.merch.pickup",
  disabled,
  offlineHint,
}: Props) {
  if (disabled) {
    return (
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
            Pickup code
          </span>
          <Badge tone="outline" size="sm">
            {pickupCode}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Pickup QR unavailable for this status.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
          Pickup code
        </span>
        <Badge tone="dark" size="sm">
          {pickupCode}
        </Badge>
      </div>
      {qrToken ? (
        <div
          className="inline-block rounded-[var(--radius-xl)] bg-paper p-3 shadow-[var(--shadow)] ring-1 ring-border"
          role="img"
          aria-label="Merch pickup QR code"
        >
          <QRCodeSVG
            value={qrToken}
            size={168}
            level="M"
            includeMargin
            bgColor="#ffffff"
            fgColor="#000000"
          />
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Show this code at the merch stand after payment confirms.
        </p>
      )}
      {offlineHint ? (
        <p className="text-xs text-muted-foreground">{offlineHint}</p>
      ) : null}
      <p className="text-[10px] text-muted-foreground">
        Merch QR ({qrTyp}) — not a ticket entry pass.
      </p>
    </div>
  );
}
