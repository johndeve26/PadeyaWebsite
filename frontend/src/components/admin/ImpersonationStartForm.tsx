"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  Alert,
  Button,
  Checkbox,
  Input,
  Select,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import type { ImpersonationDurationMinutes } from "@/lib/auth/types";
import type { UserPublic } from "@/lib/types/lifecycle";

export type ImpersonationStartFormProps = {
  userId: string;
  target?: Pick<UserPublic, "full_name" | "email" | "id" | "roles" | "is_active"> | null;
  targetLabel?: string;
  /** When set, render cancel and put primary submit in a footer-friendly layout. */
  onCancel?: () => void;
  onStarted?: () => void;
  submitLabel?: string;
};

export function ImpersonationStartForm({
  userId,
  target,
  targetLabel,
  onCancel,
  onStarted,
  submitLabel = "Start impersonation",
}: ImpersonationStartFormProps) {
  const router = useRouter();
  const toast = useToast();
  const { startImpersonation } = useAuth();
  const [reason, setReason] = useState("");
  const [ticketId, setTicketId] = useState("");
  const [duration, setDuration] = useState<ImpersonationDurationMinutes>(30);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reasonOk = reason.trim().length >= 3;
  const canSubmit = reasonOk && confirmed && Boolean(userId.trim()) && !busy;

  const summaryEmail = target?.email?.trim() || null;
  const summaryLabel =
    targetLabel ||
    (target
      ? `${target.full_name}${summaryEmail ? ` (${summaryEmail})` : ""}`
      : undefined);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    try {
      const redirectTo = await startImpersonation({
        userId: userId.trim(),
        reason: reason.trim(),
        supportTicketId: ticketId.trim() || undefined,
        durationMinutes: duration,
      });
      toast.push({
        tone: "success",
        title: "Impersonation started",
        description: "You are viewing Pàdéyá as this user. Actions are audited.",
      });
      onStarted?.();
      router.push(redirectTo || "/dashboard");
    } catch (err) {
      const detail =
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Could not start impersonation";
      setError(detail);
      toast.push({
        tone: "danger",
        title: "Impersonation failed",
        description: detail,
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={(e) => void onSubmit(e)} className="space-y-5">
      {target ? (
        <div className="rounded-[var(--radius-md)] border border-border bg-surface-muted/50 px-3 py-3 text-sm dark:bg-surface-inset/40">
          <p className="font-bold text-foreground">{target.full_name}</p>
          <p className="text-muted-foreground">
            {summaryEmail || target.email}
          </p>
          <dl className="mt-2 grid gap-1 text-xs text-muted-foreground sm:grid-cols-2">
            <div>
              <dt className="inline">Status: </dt>
              <dd className="inline font-medium text-foreground">
                {target.is_active ? "Active" : "Inactive"}
              </dd>
            </div>
            <div>
              <dt className="inline">Roles: </dt>
              <dd className="inline font-medium text-foreground">
                {target.roles.join(", ") || "—"}
              </dd>
            </div>
          </dl>
        </div>
      ) : null}

      <Alert tone="warning" title="Audited session">
        {summaryLabel ? (
          <>
            You are about to impersonate <strong>{summaryLabel}</strong>.{" "}
          </>
        ) : null}
        This is not a real login — passwords are never exposed, sensitive actions are
        blocked, and every request is audited.
      </Alert>

      <Textarea
        label="Reason"
        name="reason"
        required
        rows={3}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="e.g. Verify host payout screen for support case"
        hint="Required. At least 3 characters. Stored in the audit log."
      />

      <Input
        label="Support ticket ID"
        name="support_ticket_id"
        value={ticketId}
        onChange={(e) => setTicketId(e.target.value)}
        placeholder="Optional — e.g. SUP-1234"
        hint="Optional. Linked in the audit trail when provided."
      />

      <Select
        label="Duration"
        name="duration_minutes"
        value={String(duration)}
        onChange={(e) =>
          setDuration(Number(e.target.value) as ImpersonationDurationMinutes)
        }
        hint="Session ends automatically when the access token expires."
      >
        <option value="15">15 minutes</option>
        <option value="30">30 minutes</option>
        <option value="60">60 minutes</option>
      </Select>

      <Checkbox
        id="impersonation-confirm"
        name="confirmed"
        checked={confirmed}
        onChange={(e) => setConfirmed(e.target.checked)}
        label="I understand this session is audited and sensitive actions are blocked."
      />

      {error ? (
        <Alert tone="danger" title="Could not start">
          {error}
        </Alert>
      ) : null}

      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:flex-wrap sm:justify-end">
        {onCancel ? (
          <Button type="button" variant="secondary" disabled={busy} onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
        <Button type="submit" disabled={!canSubmit}>
          {busy ? "Starting…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
