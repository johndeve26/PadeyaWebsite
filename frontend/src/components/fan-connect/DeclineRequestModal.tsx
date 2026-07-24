"use client";

import { useEffect, useState } from "react";

import { Button, Modal } from "@/components/ui";
import { fetchDeclineCooldownOptions } from "@/lib/fan-connect-api";

export type DeclineCooldownChoice =
  | "default"
  | 7
  | 30
  | 90
  | 365;

type Props = {
  open: boolean;
  onClose: () => void;
  onConfirm: (cooldownDays: number | null) => void | Promise<void>;
  busy?: boolean;
};

const OPTIONS: { value: DeclineCooldownChoice; label: string }[] = [
  { value: "default", label: "Platform default" },
  { value: 7, label: "7 days" },
  { value: 30, label: "30 days" },
  { value: 90, label: "90 days" },
  { value: 365, label: "365 days" },
];

export function DeclineRequestModal({
  open,
  onClose,
  onConfirm,
  busy = false,
}: Props) {
  const [choice, setChoice] = useState<DeclineCooldownChoice>("default");
  const [platformDefault, setPlatformDefault] = useState<number | null>(null);

  useEffect(() => {
    if (!open) return;
    let active = true;
    void (async () => {
      try {
        const settings = await fetchDeclineCooldownOptions();
        if (!active) return;
        setPlatformDefault(settings.default_cooldown_days);
      } catch {
        if (active) setPlatformDefault(30);
      }
    })();
    return () => {
      active = false;
    };
  }, [open]);

  async function submit() {
    const cooldownDays = choice === "default" ? null : choice;
    await onConfirm(cooldownDays);
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Decline request"
      description="This only pauses new requests from them to you. You can still connect later if you want."
    >
      <fieldset className="space-y-3">
        <legend className="text-sm font-semibold text-foreground">
          When can this person request again?
        </legend>
        {OPTIONS.map((opt) => (
          <label
            key={String(opt.value)}
            className="flex cursor-pointer items-center gap-3 rounded-[var(--radius-md)] border border-border px-3 py-2 text-sm"
          >
            <input
              type="radio"
              name="decline-cooldown"
              checked={choice === opt.value}
              onChange={() => setChoice(opt.value)}
              className="size-4"
            />
            <span>
              {opt.label}
              {opt.value === "default" && platformDefault != null
                ? ` (${platformDefault} day${platformDefault === 1 ? "" : "s"})`
                : null}
            </span>
          </label>
        ))}
      </fieldset>
      <div className="mt-6 flex flex-wrap justify-end gap-2">
        <Button variant="secondary" onClick={onClose} disabled={busy}>
          Cancel
        </Button>
        <Button onClick={() => void submit()} disabled={busy}>
          Decline request
        </Button>
      </div>
    </Modal>
  );
}
