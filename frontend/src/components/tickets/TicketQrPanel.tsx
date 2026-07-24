import { QRCodeSVG } from "qrcode.react";

import { cn } from "@/lib/cn";

/**
 * High-contrast QR panel for door scanning.
 * Always renders on a fixed white plate — never theme-flipped.
 */
export function TicketQrPanel({
  value,
  size = 280,
  className = "",
}: {
  value: string;
  size?: number;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "w-full max-w-[280px] rounded-[var(--radius-xl)] bg-paper p-3 shadow-[var(--shadow)] ring-1 ring-border sm:p-4",
        className,
      )}
      role="img"
      aria-label="Ticket QR code"
    >
      <QRCodeSVG
        value={value}
        size={size}
        level="M"
        includeMargin
        bgColor="#ffffff"
        fgColor="#000000"
        className="mx-auto h-auto w-full max-w-[280px]"
      />
    </div>
  );
}
