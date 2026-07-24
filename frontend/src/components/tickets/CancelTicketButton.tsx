"use client";

import { useState } from "react";

import { Button, Input, Modal } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { cancelTicket } from "@/lib/advanced-tickets-api";

type CancelTicketButtonProps = {
  ticketId: string;
  reason?: string;
  label?: string;
  size?: "sm" | "md" | "lg";
  variant?: "primary" | "secondary" | "ghost" | "danger" | "dark";
  className?: string;
  disabled?: boolean;
  onCancelled?: () => void | Promise<void>;
  onError?: (message: string) => void;
};

/**
 * Destructive cancel: requires account password and warns that cancel is irreversible.
 */
export function CancelTicketButton({
  ticketId,
  reason = "Ticket cancellation",
  label = "Cancel ticket",
  size = "sm",
  variant = "danger",
  className,
  disabled,
  onCancelled,
  onError,
}: CancelTicketButtonProps) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  function close() {
    if (pending) return;
    setOpen(false);
    setPassword("");
    setLocalError(null);
  }

  async function handleConfirm() {
    if (!password) {
      setLocalError("Enter your password to cancel this ticket.");
      return;
    }
    setPending(true);
    setLocalError(null);
    try {
      await cancelTicket(ticketId, { password, reason });
      setOpen(false);
      setPassword("");
      await onCancelled?.();
    } catch (err) {
      const message =
        err instanceof ApiError ? err.detail : "Cancel failed. Ticket was not cancelled.";
      setLocalError(message);
      onError?.(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <Button
        size={size}
        variant={variant}
        className={className}
        disabled={disabled || pending}
        onClick={() => setOpen(true)}
      >
        {label}
      </Button>
      <Modal
        open={open}
        onClose={close}
        title="Cancel this ticket?"
        description="This cannot be undone. The QR code will stop working at the door and you will not be able to restore this ticket."
        footer={
          <>
            <Button variant="ghost" size="sm" disabled={pending} onClick={close}>
              Keep ticket
            </Button>
            <Button
              size="sm"
              variant="danger"
              disabled={pending || !password}
              onClick={() => void handleConfirm()}
            >
              {pending ? "Cancelling…" : "Cancel ticket permanently"}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="rounded-[var(--radius-md)] border border-danger bg-danger-soft/60 px-3 py-3 text-sm leading-relaxed text-foreground">
            <p className="font-bold text-danger">Irreversible</p>
            <p className="mt-1 text-muted-foreground">
              Cancellation is permanent. Entry will be rejected. Refunds (if any) are
              handled separately and are not guaranteed by cancelling here.
            </p>
          </div>
          <Input
            label="Your password"
            type="password"
            name="cancel-ticket-password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (localError) setLocalError(null);
            }}
            error={localError ?? undefined}
            hint="Type your account password to confirm. This prevents accidental cancellation."
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void handleConfirm();
              }
            }}
          />
        </div>
      </Modal>
    </>
  );
}
