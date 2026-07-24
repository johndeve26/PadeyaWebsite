"use client";

import { type ReactNode, useState } from "react";

import { Button, type ButtonProps } from "./Button";
import { Input } from "./Input";
import { Modal } from "./Modal";
import { Textarea } from "./Textarea";

type ConfirmActionProps = {
  label: string;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Use danger styling for irreversible / finance actions */
  tone?: "danger" | "default";
  disabled?: boolean;
  busy?: boolean;
  size?: ButtonProps["size"];
  variant?: ButtonProps["variant"];
  children?: ReactNode;
  /** Require a typed reason before confirm (sensitive lifecycle actions). */
  requireReason?: boolean;
  reasonLabel?: string;
  reasonPlaceholder?: string;
  reasonMinLength?: number;
  onConfirm: (reason?: string) => void | Promise<void>;
};

/**
 * Button that opens a confirmation modal before running a destructive or
 * finance-sensitive action. Does not change underlying API contracts.
 */
export function ConfirmAction({
  label,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "default",
  disabled,
  busy,
  size = "sm",
  variant,
  children,
  requireReason = false,
  reasonLabel = "Reason",
  reasonPlaceholder = "Explain why you are taking this action…",
  reasonMinLength = 3,
  onConfirm,
}: ConfirmActionProps) {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);

  const buttonVariant =
    variant ?? (tone === "danger" ? "danger" : "secondary");

  async function handleConfirm() {
    if (requireReason) {
      const trimmed = reason.trim();
      if (trimmed.length < reasonMinLength) {
        setReasonError(`Enter at least ${reasonMinLength} characters.`);
        return;
      }
    }
    setPending(true);
    setReasonError(null);
    try {
      await onConfirm(requireReason ? reason.trim() : undefined);
      setOpen(false);
      setReason("");
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <Button
        size={size}
        variant={buttonVariant}
        disabled={disabled || busy}
        onClick={() => setOpen(true)}
      >
        {label}
      </Button>
      <Modal
        open={open}
        onClose={() => {
          if (!pending) {
            setOpen(false);
            setReason("");
            setReasonError(null);
          }
        }}
        title={title}
        description={description}
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              disabled={pending}
              onClick={() => {
                setOpen(false);
                setReason("");
                setReasonError(null);
              }}
            >
              {cancelLabel}
            </Button>
            <Button
              size="sm"
              variant={tone === "danger" ? "danger" : "dark"}
              disabled={pending}
              onClick={() => void handleConfirm()}
            >
              {pending ? "Working…" : confirmLabel}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          {children ?? (
            <p className="text-sm text-muted-foreground">
              This action is recorded for audit. Continue only if you have verified
              the case details.
            </p>
          )}
          {requireReason ? (
            <Textarea
              label={reasonLabel}
              hint="Required for sensitive lifecycle changes."
              placeholder={reasonPlaceholder}
              value={reason}
              error={reasonError ?? undefined}
              onChange={(e) => {
                setReason(e.target.value);
                if (reasonError) setReasonError(null);
              }}
              rows={3}
            />
          ) : null}
        </div>
      </Modal>
    </>
  );
}

/** Compact confirmation that uses Input instead of Textarea for short reasons. */
export function ConfirmActionWithCode({
  codeLabel = "Type ARCHIVE to confirm",
  expected = "ARCHIVE",
  ...props
}: ConfirmActionProps & { codeLabel?: string; expected?: string }) {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [code, setCode] = useState("");

  async function handleConfirm() {
    if (code.trim().toUpperCase() !== expected.toUpperCase()) return;
    setPending(true);
    try {
      await props.onConfirm();
      setOpen(false);
      setCode("");
    } finally {
      setPending(false);
    }
  }

  const buttonVariant =
    props.variant ?? (props.tone === "danger" ? "danger" : "secondary");

  return (
    <>
      <Button
        size={props.size ?? "sm"}
        variant={buttonVariant}
        disabled={props.disabled || props.busy}
        onClick={() => setOpen(true)}
      >
        {props.label}
      </Button>
      <Modal
        open={open}
        onClose={() => {
          if (!pending) {
            setOpen(false);
            setCode("");
          }
        }}
        title={props.title}
        description={props.description}
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              disabled={pending}
              onClick={() => setOpen(false)}
            >
              {props.cancelLabel ?? "Cancel"}
            </Button>
            <Button
              size="sm"
              variant={props.tone === "danger" ? "danger" : "dark"}
              disabled={pending || code.trim().toUpperCase() !== expected.toUpperCase()}
              onClick={() => void handleConfirm()}
            >
              {pending ? "Working…" : (props.confirmLabel ?? "Confirm")}
            </Button>
          </>
        }
      >
        <Input
          label={codeLabel}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          hint={`Type ${expected} to enable confirm.`}
        />
      </Modal>
    </>
  );
}
