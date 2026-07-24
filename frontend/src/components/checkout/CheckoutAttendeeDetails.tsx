"use client";

import { Input } from "@/components/ui";
import type {
  AttendeeDraft,
  GiftDelivery,
  PurchaseMode,
} from "@/components/checkout/types";

type Props = {
  mode: PurchaseMode;
  selfName: string;
  selfEmail: string;
  onSelfChange: (field: "name" | "email", value: string) => void;
  recipientName: string;
  recipientEmail: string;
  onRecipientChange: (field: "name" | "email", value: string) => void;
  gift: GiftDelivery;
  onGiftChange: (next: GiftDelivery) => void;
  useSameForAll: boolean;
  onUseSameForAll: (value: boolean) => void;
  attendees: AttendeeDraft[];
  onAttendeeChange: (index: number, next: AttendeeDraft) => void;
};

export function CheckoutAttendeeDetails({
  mode,
  selfName,
  selfEmail,
  onSelfChange,
  recipientName,
  recipientEmail,
  onRecipientChange,
  gift,
  onGiftChange,
  useSameForAll,
  onUseSameForAll,
  attendees,
  onAttendeeChange,
}: Props) {
  return (
    <div className="space-y-5">
      {mode === "self" ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            These details appear on the ticket. Edit if you need a different name
            or email for entry.
          </p>
          <Input
            label="Full name"
            value={selfName}
            onChange={(e) => onSelfChange("name", e.target.value)}
            autoComplete="name"
          />
          <Input
            label="Email"
            type="email"
            value={selfEmail}
            onChange={(e) => onSelfChange("email", e.target.value)}
            autoComplete="email"
          />
        </div>
      ) : null}

      {mode === "other" ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            You remain the buyer. The ticket is assigned to the recipient below.
          </p>
          <Input
            label="Recipient full name"
            value={recipientName}
            onChange={(e) => onRecipientChange("name", e.target.value)}
          />
          <Input
            label="Recipient email"
            type="email"
            value={recipientEmail}
            onChange={(e) => onRecipientChange("email", e.target.value)}
            hint="We’ll email ticket access instructions to this address when payment confirms."
          />
          <Input
            label="Gift message (optional)"
            value={gift.gift_message}
            onChange={(e) =>
              onGiftChange({ ...gift, gift_message: e.target.value })
            }
            hint="Shown in the recipient email — keep it short."
          />
          <label className="flex min-h-11 items-start gap-3 text-sm text-foreground">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-[var(--primary)]"
              checked={gift.send_ticket_to_recipient}
              onChange={(e) =>
                onGiftChange({
                  ...gift,
                  send_ticket_to_recipient: e.target.checked,
                })
              }
            />
            <span>Send ticket to recipient</span>
          </label>
          <label className="flex min-h-11 items-start gap-3 text-sm text-foreground">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-[var(--primary)]"
              checked={gift.keep_buyer_copy}
              onChange={(e) =>
                onGiftChange({
                  ...gift,
                  keep_buyer_copy: e.target.checked,
                })
              }
            />
            <span>Keep a buyer copy in My Tickets</span>
          </label>
        </div>
      ) : null}

      {mode === "group" ? (
        <div className="space-y-4">
          <label className="flex min-h-11 items-start gap-3 text-sm text-foreground">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-[var(--primary)]"
              checked={useSameForAll}
              onChange={(e) => onUseSameForAll(e.target.checked)}
            />
            <span>Use the same buyer details for all tickets</span>
          </label>
          {useSameForAll ? (
            <div className="space-y-3">
              <Input
                label="Attendee full name"
                value={selfName}
                onChange={(e) => onSelfChange("name", e.target.value)}
              />
              <Input
                label="Attendee email"
                type="email"
                value={selfEmail}
                onChange={(e) => onSelfChange("email", e.target.value)}
              />
            </div>
          ) : (
            <ul className="space-y-4">
              {attendees.map((row, index) => (
                <li
                  key={`${row.ticket_type_id}-${row.unit_index}`}
                  className="space-y-3 border-t border-border pt-4 first:border-0 first:pt-0"
                >
                  <p className="text-sm font-bold text-foreground">
                    {row.ticket_label} · ticket {row.unit_index + 1}
                  </p>
                  <Input
                    label="Full name"
                    value={row.attendee_name}
                    onChange={(e) =>
                      onAttendeeChange(index, {
                        ...row,
                        attendee_name: e.target.value,
                      })
                    }
                  />
                  <Input
                    label="Email"
                    type="email"
                    value={row.attendee_email}
                    onChange={(e) =>
                      onAttendeeChange(index, {
                        ...row,
                        attendee_email: e.target.value,
                      })
                    }
                  />
                  <Input
                    label="Phone (optional)"
                    value={row.attendee_phone}
                    onChange={(e) =>
                      onAttendeeChange(index, {
                        ...row,
                        attendee_phone: e.target.value,
                      })
                    }
                  />
                </li>
              ))}
            </ul>
          )}
          <label className="flex min-h-11 items-start gap-3 text-sm text-foreground">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-[var(--primary)]"
              checked={gift.send_ticket_to_recipient}
              onChange={(e) =>
                onGiftChange({
                  ...gift,
                  send_ticket_to_recipient: e.target.checked,
                })
              }
            />
            <span>Email tickets to each attendee after confirmation</span>
          </label>
          <label className="flex min-h-11 items-start gap-3 text-sm text-foreground">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-[var(--primary)]"
              checked={gift.keep_buyer_copy}
              onChange={(e) =>
                onGiftChange({
                  ...gift,
                  keep_buyer_copy: e.target.checked,
                })
              }
            />
            <span>Keep a buyer copy in My Tickets</span>
          </label>
        </div>
      ) : null}
    </div>
  );
}
