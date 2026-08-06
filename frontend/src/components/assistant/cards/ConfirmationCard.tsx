"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import {
  cancelAssistantAction,
  confirmAssistantAction,
} from "@/lib/assistant-api";
import type { AssistantCard } from "@/lib/types/assistant";

export function ConfirmationCard({
  card,
  confirmationId,
  onDone,
}: {
  card: AssistantCard;
  confirmationId?: string | null;
  onDone?: (result: "confirmed" | "cancelled" | "error", detail?: string) => void;
}) {
  const id =
    confirmationId ||
    (typeof card.meta?.confirmation_id === "string"
      ? card.meta.confirmation_id
      : null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<"idle" | "confirmed" | "cancelled" | "error">(
    "idle",
  );
  const [error, setError] = useState<string | null>(null);

  async function onConfirm() {
    if (!id || busy) return;
    setBusy(true);
    setError(null);
    try {
      await confirmAssistantAction(id);
      setStatus("confirmed");
      onDone?.("confirmed");
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Confirm failed";
      setStatus("error");
      setError(detail);
      onDone?.("error", detail);
    } finally {
      setBusy(false);
    }
  }

  async function onCancel() {
    if (!id || busy) return;
    setBusy(true);
    setError(null);
    try {
      await cancelAssistantAction(id);
      setStatus("cancelled");
      onDone?.("cancelled");
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Cancel failed";
      setStatus("error");
      setError(detail);
      onDone?.("error", detail);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-[var(--radius-md)] border border-border bg-surface-elevated p-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
        Confirm action
      </p>
      <p className="mt-1 text-sm font-bold text-heading">{card.title}</p>
      {card.subtitle ? (
        <p className="mt-1 text-xs text-muted-foreground">{card.subtitle}</p>
      ) : null}

      {status === "idle" && id ? (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="primary"
            disabled={busy}
            onClick={() => void onConfirm()}
          >
            Confirm
          </Button>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => void onCancel()}
          >
            Cancel
          </Button>
        </div>
      ) : null}

      {status === "confirmed" ? (
        <p className="mt-2 text-xs font-semibold text-primary-text">Confirmed.</p>
      ) : null}
      {status === "cancelled" ? (
        <p className="mt-2 text-xs text-muted-foreground">Cancelled.</p>
      ) : null}
      {error ? (
        <p className="mt-2 text-xs text-danger" role="alert">
          {error}
        </p>
      ) : null}
      {!id ? (
        <p className="mt-2 text-xs text-muted-foreground">
          Confirmation unavailable.
        </p>
      ) : null}
    </div>
  );
}
