"use client";

import { useCallback, useState, type FormEvent } from "react";

import { QrScanner } from "@/components/checkin/QrScanner";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  Alert,
  Badge,
  Button,
  Input,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { formatDateTime } from "@/lib/format";
import { scanMerchPickup } from "@/lib/merch-api";
import type { MerchFulfillment } from "@/lib/types/merch";

type Props = {
  eventId: string;
  onPickedUp?: () => void | Promise<void>;
};

/**
 * Event merch fulfillment desk — scan padeya.merch.pickup QR or enter MRCH-* code.
 * Ticket QR (padeya.ticket.qr) is rejected server-side.
 */
export function HostMerchPickupDesk({ eventId, onPickedUp }: Props) {
  const toast = useToast();
  const { user } = useAuth();
  const canFulfill = userHasPermission(user, "merch.fulfill", "merch.manage_own");
  const [manualCode, setManualCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [last, setLast] = useState<MerchFulfillment | null>(null);

  const runScan = useCallback(
    async (payload: { token?: string; pickup_code?: string }) => {
      if (!canFulfill) {
        setError("Merch fulfill permission required.");
        return;
      }
      setBusy(true);
      setPaused(true);
      setError(null);
      try {
        const row = await scanMerchPickup(eventId, payload);
        setLast(row);
        toast.push({ tone: "success", title: "Merch pickup confirmed" });
        await onPickedUp?.();
      } catch (err) {
        const detail =
          err instanceof ApiError ? err.detail : "Merch scan failed";
        setError(detail);
        toast.push({ tone: "danger", title: detail });
      } finally {
        setBusy(false);
        window.setTimeout(() => setPaused(false), 1800);
      }
    },
    [canFulfill, eventId, onPickedUp, toast],
  );

  async function onManual(event: FormEvent) {
    event.preventDefault();
    const code = manualCode.trim().toUpperCase();
    if (!code) return;
    await runScan({ pickup_code: code });
  }

  if (!canFulfill) {
    return (
      <p className="text-sm text-muted-foreground">
        View only — scanning merch QR requires merch fulfill permission.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
          Merch QR desk
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Scan a Pàdéyá merch pickup QR ({`typ=padeya.merch.pickup`}) or enter an
          MRCH code. Ticket entry QR is not accepted here.
        </p>
      </div>

      <QrScanner
        readerId="padeya-merch-qr-reader"
        onScan={(value) => {
          const trimmed = value.trim();
          if (!trimmed || busy) return;
          if (trimmed.toUpperCase().startsWith("MRCH-")) {
            void runScan({ pickup_code: trimmed.toUpperCase() });
            return;
          }
          void runScan({ token: trimmed });
        }}
        paused={paused || busy}
      />

      <form
        className="grid gap-2 sm:grid-cols-[1fr_auto] sm:items-end"
        onSubmit={(e) => void onManual(e)}
      >
        <Input
          label="Or enter pickup code"
          placeholder="MRCH-…"
          value={manualCode}
          onChange={(e) => setManualCode(e.target.value)}
          autoComplete="off"
          spellCheck={false}
        />
        <Button type="submit" size="sm" disabled={busy || !manualCode.trim()}>
          Confirm pickup
        </Button>
      </form>

      {error ? (
        <Alert tone="danger" title="Pickup blocked">
          {error}
        </Alert>
      ) : null}

      {last ? (
        <div className="space-y-2 rounded-[var(--radius-md)] border border-border bg-muted/30 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="dark" size="sm">
              {last.pickup_code}
            </Badge>
            <StatusBadge status="picked_up" label="Picked up" />
          </div>
          <p className="font-extrabold tracking-tight text-foreground">
            {last.product_name_snapshot}
          </p>
          <p className="text-sm text-muted-foreground">
            {last.variant_label_snapshot} · Qty {last.quantity}
          </p>
          <p className="text-xs font-semibold text-foreground">
            Collected
            {last.fulfilled_at ? ` ${formatDateTime(last.fulfilled_at)}` : ""}
            {last.fulfilled_by_name ? ` · ${last.fulfilled_by_name}` : ""}
          </p>
        </div>
      ) : null}
    </div>
  );
}
