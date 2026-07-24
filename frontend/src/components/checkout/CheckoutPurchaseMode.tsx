"use client";

import type { PurchaseMode } from "@/components/checkout/types";

const MODES: {
  id: PurchaseMode;
  title: string;
  hintSignedIn: string;
  hintGuest: string;
}[] = [
  {
    id: "self",
    title: "Buy for myself",
    hintSignedIn:
      "Ticket details are prefilled from your account — you can still edit them.",
    hintGuest: "Enter the name and email that should appear on your ticket.",
  },
  {
    id: "other",
    title: "Buy for someone else",
    hintSignedIn:
      "You pay; the ticket is assigned to the recipient. Delivery is your choice.",
    hintGuest:
      "You pay; the ticket is assigned to the recipient. Delivery is your choice.",
  },
  {
    id: "group",
    title: "Buy for a group",
    hintSignedIn:
      "Assign each ticket to an attendee, or use the same details for all.",
    hintGuest:
      "Assign each ticket to an attendee, or use the same details for all.",
  },
];

type Props = {
  value: PurchaseMode;
  onChange: (mode: PurchaseMode) => void;
  disabled?: boolean;
  /** When true, self-mode copy references account prefill. */
  signedIn?: boolean;
};

export function CheckoutPurchaseMode({
  value,
  onChange,
  disabled,
  signedIn = false,
}: Props) {
  return (
    <fieldset className="space-y-3" disabled={disabled}>
      <legend className="text-sm font-bold text-foreground">Who is this for?</legend>
      <div className="space-y-2">
        {MODES.map((mode) => {
          const selected = value === mode.id;
          return (
            <label
              key={mode.id}
              className={[
                "flex min-h-12 cursor-pointer gap-3 rounded-[var(--radius-md)] border px-4 py-3 transition",
                selected
                  ? "border-primary bg-primary/10"
                  : "border-border bg-card hover:border-foreground/30",
              ].join(" ")}
            >
              <input
                type="radio"
                name="purchase_mode"
                className="mt-1 h-4 w-4 accent-[var(--primary)]"
                checked={selected}
                onChange={() => onChange(mode.id)}
              />
              <span className="min-w-0">
                <span className="block text-sm font-bold text-foreground">
                  {mode.title}
                </span>
                <span className="mt-0.5 block text-xs leading-relaxed text-muted-foreground">
                  {signedIn ? mode.hintSignedIn : mode.hintGuest}
                </span>
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
