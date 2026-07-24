"use client";

import { useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

import { Button } from "@/components/ui";
import { formatAmbassadorCodeDisplay } from "@/lib/ambassador-referral";
import { cn } from "@/lib/cn";

/**
 * Shareable Ambassador QR card — uses existing qrcode.react utility.
 * Download exports a PNG of the card for stories / WhatsApp.
 */
export function AmbassadorShareCard({
  eventTitle,
  code,
  link,
  campaignLabel,
  className = "",
}: {
  eventTitle: string;
  code: string;
  link: string;
  campaignLabel?: string | null;
  className?: string;
}) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const display = formatAmbassadorCodeDisplay(code);

  async function downloadPng() {
    const node = cardRef.current;
    if (!node) return;
    setBusy(true);
    setNote(null);
    try {
      const svg = node.querySelector("svg");
      if (!svg) throw new Error("QR missing");
      const serializer = new XMLSerializer();
      const svgText = serializer.serializeToString(svg);
      const blob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const img = new Image();
      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve();
        img.onerror = () => reject(new Error("QR render failed"));
        img.src = url;
      });
      const canvas = document.createElement("canvas");
      const width = 720;
      const height = 900;
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Canvas unavailable");
      ctx.fillStyle = "#0f1712";
      ctx.fillRect(0, 0, width, height);
      ctx.fillStyle = "#f4f7f4";
      ctx.font = "700 28px Georgia, serif";
      ctx.fillText("Pàdéyá Ambassadors", 48, 72);
      ctx.font = "600 36px Georgia, serif";
      const title = eventTitle.slice(0, 42);
      ctx.fillText(title, 48, 130);
      if (campaignLabel) {
        ctx.font = "500 22px system-ui, sans-serif";
        ctx.fillStyle = "#a8b5a8";
        ctx.fillText(campaignLabel, 48, 170);
      }
      const qrSize = 360;
      const qrX = (width - qrSize) / 2;
      const qrY = 220;
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(qrX - 24, qrY - 24, qrSize + 48, qrSize + 48);
      ctx.drawImage(img, qrX, qrY, qrSize, qrSize);
      ctx.fillStyle = "#f4f7f4";
      ctx.font = "700 40px ui-monospace, monospace";
      ctx.textAlign = "center";
      ctx.fillText(display, width / 2, qrY + qrSize + 80);
      ctx.font = "500 18px system-ui, sans-serif";
      ctx.fillStyle = "#a8b5a8";
      ctx.fillText("Scan or use code at checkout", width / 2, qrY + qrSize + 120);
      URL.revokeObjectURL(url);
      const png = canvas.toDataURL("image/png");
      const a = document.createElement("a");
      a.href = png;
      a.download = `padeya-ambassador-${display.toLowerCase()}.png`;
      a.click();
      setNote("QR card downloaded");
    } catch {
      setNote("Could not download QR card");
    } finally {
      setBusy(false);
      window.setTimeout(() => setNote(null), 2000);
    }
  }

  async function shareNative() {
    if (typeof navigator === "undefined" || !navigator.share) {
      setNote("Share not supported — download the card instead");
      window.setTimeout(() => setNote(null), 2000);
      return;
    }
    try {
      await navigator.share({
        title: `${eventTitle} — Pàdéyá Ambassadors`,
        text: `Use my Ambassador code ${display}`,
        url: link,
      });
    } catch {
      /* user cancelled */
    }
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div
        ref={cardRef}
        className="rounded-[var(--radius-xl)] border border-border bg-card p-4 shadow-[var(--shadow-soft)]"
      >
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Share card
        </p>
        <p className="mt-1 text-sm font-semibold text-foreground">{eventTitle}</p>
        {campaignLabel ? (
          <p className="text-xs text-muted-foreground">{campaignLabel}</p>
        ) : null}
        <div className="mx-auto mt-3 w-full max-w-[200px] rounded-[var(--radius-lg)] bg-paper p-3">
          <QRCodeSVG
            value={link}
            size={176}
            level="M"
            includeMargin
            bgColor="#ffffff"
            fgColor="#000000"
            className="mx-auto h-auto w-full"
          />
        </div>
        <p className="mt-3 text-center font-mono text-lg font-bold tracking-wide text-foreground">
          {display}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => void downloadPng()}
        >
          {busy ? "Preparing…" : "Download QR card"}
        </Button>
        <Button size="sm" variant="secondary" onClick={() => void shareNative()}>
          Share
        </Button>
      </div>
      {note ? <p className="text-xs text-muted-foreground">{note}</p> : null}
    </div>
  );
}
