"use client";

import { TicketKindField } from "@/components/events/TicketKindField";
import {
  Button,
  ConfirmAction,
  EmptyState,
  Input,
  Select,
  Textarea,
} from "@/components/ui";

import { StudioItemCard, StudioMicrocopy } from "./studio-ui";
import {
  ticketHasSales,
  ticketSaleWindowError,
  type StudioTicketDraft,
} from "./types";

function newDraft(partial?: Partial<StudioTicketDraft>): StudioTicketDraft {
  return {
    localId: `draft-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    name: "",
    type: "regular",
    description: "",
    price: "0",
    quantity: "100",
    seats_per_unit: "1",
    min_per_order: "1",
    max_per_order: "10",
    sale_start: "",
    sale_end: "",
    visibility: "public",
    benefits: "",
    transfer_allowed: true,
    refund_allowed: false,
    access_code: "",
    waitlist_enabled: false,
    table_perks: "",
    reservation_hold_minutes: "",
    quantity_sold: 0,
    quantity_reserved: 0,
    status: "active",
    ...partial,
  };
}

function applyTypeDefaults(
  type: string,
  draft: StudioTicketDraft,
): Partial<StudioTicketDraft> {
  const patch: Partial<StudioTicketDraft> = { type };
  if (type === "free_rsvp" || type === "free") {
    patch.price = "0";
  }
  if (type === "hidden" || type === "invite_only") {
    patch.visibility = type;
  } else if (
    draft.visibility === "hidden" ||
    draft.visibility === "invite_only"
  ) {
    patch.visibility = "public";
  }
  if (type === "table" && Number(draft.seats_per_unit || 1) < 2) {
    patch.seats_per_unit = "4";
  }
  if (type === "group" && Number(draft.seats_per_unit || 1) < 2) {
    patch.seats_per_unit = "2";
  }
  return patch;
}

export function TicketTypeBuilder({
  drafts,
  onChange,
  eventId,
  onDeactivate,
  onDeleteUnused,
  allowStructuralEdits = false,
}: {
  drafts: StudioTicketDraft[];
  onChange: (drafts: StudioTicketDraft[]) => void;
  eventId?: string;
  /** Deactivate a sold/saved tier (preferred over delete after sales). */
  onDeactivate?: (ticketTypeId: string) => Promise<void> | void;
  /** Hard-delete an unused saved tier. */
  onDeleteUnused?: (ticketTypeId: string) => Promise<void> | void;
  /** When true (admin impersonation), unlock price/name/qty after sales. */
  allowStructuralEdits?: boolean;
}) {
  function update(localId: string, patch: Partial<StudioTicketDraft>) {
    onChange(
      drafts.map((d) => (d.localId === localId ? { ...d, ...patch } : d)),
    );
  }

  async function removeDraft(draft: StudioTicketDraft) {
    if (!draft.id) {
      onChange(drafts.filter((d) => d.localId !== draft.localId));
      return;
    }
    if (ticketHasSales(draft)) {
      if (onDeactivate) {
        await onDeactivate(draft.id);
        update(draft.localId, { status: "inactive" });
      }
      return;
    }
    if (onDeleteUnused) {
      await onDeleteUnused(draft.id);
    }
    onChange(drafts.filter((d) => d.localId !== draft.localId));
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm font-semibold text-foreground">Ticket types</p>
        <StudioMicrocopy>
          Create and edit tiers before sales begin. After sales, sold tiers stay
          for order history — deactivate instead of deleting. Unused tiers can
          be deleted. Changes sync when you save
          {eventId ? "." : " (after the event draft is created)."}
        </StudioMicrocopy>
      </div>
      {drafts.length === 0 ? (
        <EmptyState
          title="No ticket types yet"
          description="Start with Early Bird, Regular, and VIP — or Free RSVP for open nights."
          action={
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                onChange([
                  newDraft({ name: "Early Bird", type: "early_bird", price: "5000" }),
                  newDraft({ name: "Regular", type: "regular", price: "10000" }),
                  newDraft({ name: "VIP", type: "vip", price: "25000" }),
                ])
              }
            >
              Add starter tiers
            </Button>
          }
        />
      ) : null}
      {drafts.map((draft, index) => {
        const sold = ticketHasSales(draft);
        const saleError = ticketSaleWindowError(
          draft.sale_start,
          draft.sale_end,
        );
        const isTable = draft.type === "table";
        const isGroup = draft.type === "group";
        const locked = sold && !allowStructuralEdits;
        return (
          <StudioItemCard
            key={draft.localId}
            title={[
              `Tier ${index + 1}`,
              draft.name.trim() || null,
              !draft.id ? "New" : null,
              draft.status === "inactive" ? "Inactive" : null,
              sold ? "Has sales" : null,
            ]
              .filter(Boolean)
              .join(" · ")}
            subtitle={
              sold && allowStructuralEdits
                ? "Has sales — structural fields unlocked with host_events impersonation pack (audited)."
                : sold
                  ? "Sold/reserved inventory locks price, name, type, quantity, and seats so existing orders stay intact."
                  : undefined
            }
            actions={
              <>
                {draft.id && sold && draft.status !== "inactive" ? (
                  <ConfirmAction
                    label="Deactivate"
                    title="Deactivate this ticket type?"
                    description="Buyers can no longer purchase this tier. Existing orders and tickets stay intact."
                    confirmLabel="Deactivate"
                    variant="ghost"
                    onConfirm={() => removeDraft(draft)}
                  />
                ) : null}
                {draft.id && sold && draft.status === "inactive" ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => update(draft.localId, { status: "active" })}
                  >
                    Reactivate
                  </Button>
                ) : null}
                {!sold ? (
                  <ConfirmAction
                    label={draft.id ? "Delete" : "Remove"}
                    title={
                      draft.id
                        ? "Delete this unused ticket type?"
                        : "Remove this ticket type?"
                    }
                    description={
                      draft.id
                        ? "Permanent only when there are no sales or reservations. Prefer deactivate after sales begin."
                        : "Removes this draft tier from the Studio list before save."
                    }
                    confirmLabel={draft.id ? "Delete permanently" : "Remove"}
                    tone="danger"
                    variant="ghost"
                    onConfirm={() => removeDraft(draft)}
                  />
                ) : null}
              </>
            }
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Name"
                required
                hint="What buyers see at checkout (e.g. Early Bird, VIP, Couples)."
                value={draft.name}
                disabled={locked}
                onChange={(e) => update(draft.localId, { name: e.target.value })}
              />
              <TicketKindField
                value={draft.type}
                disabled={locked}
                onChange={(type) =>
                  update(draft.localId, applyTypeDefaults(type, draft))
                }
              />
            </div>
            <Textarea
              label="Description"
              rows={2}
              hint="Optional. What is included with this tier."
              value={draft.description}
              onChange={(e) =>
                update(draft.localId, { description: e.target.value })
              }
            />
            <div className="grid gap-3 sm:grid-cols-3">
              <Input
                label="Price (NGN)"
                type="number"
                min={0}
                hint={
                  draft.type === "free_rsvp"
                    ? "Free RSVP is always ₦0."
                    : "Amount in naira."
                }
                value={draft.price}
                disabled={locked || draft.type === "free_rsvp"}
                onChange={(e) => update(draft.localId, { price: e.target.value })}
              />
              <Input
                label="Quantity"
                type="number"
                min={0}
                hint="How many of this tier you can sell before it sells out."
                value={draft.quantity}
                disabled={locked}
                onChange={(e) =>
                  update(draft.localId, { quantity: e.target.value })
                }
              />
              <Select
                label="Visibility"
                hint="Public = everyone. Hidden / invite only = needs a link or code."
                value={draft.visibility}
                onChange={(e) =>
                  update(draft.localId, { visibility: e.target.value })
                }
              >
                <option value="public">Public</option>
                <option value="hidden">Hidden</option>
                <option value="invite_only">Invite only</option>
              </Select>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <Input
                label="Min / order"
                type="number"
                min={1}
                hint="Fewest tickets in one purchase (usually 1)."
                value={draft.min_per_order}
                disabled={locked}
                onChange={(e) =>
                  update(draft.localId, { min_per_order: e.target.value })
                }
              />
              <Input
                label="Max / order"
                type="number"
                min={1}
                hint="Most tickets one buyer can take in a single order."
                value={draft.max_per_order}
                disabled={locked}
                onChange={(e) =>
                  update(draft.localId, { max_per_order: e.target.value })
                }
              />
              <Input
                label={isTable ? "Seats per table" : "Seats per unit"}
                type="number"
                min={1}
                hint={
                  isTable
                    ? "People covered by one table purchase."
                    : isGroup
                      ? "People covered by one group unit."
                      : "Usually 1. Use 2+ for couples, groups, or tables."
                }
                value={draft.seats_per_unit}
                disabled={locked}
                onChange={(e) =>
                  update(draft.localId, { seats_per_unit: e.target.value })
                }
              />
            </div>
            <Textarea
              label="Benefits"
              rows={2}
              hint="Perks list (fast-track entry, drink token, merch). Shown on the ticket card."
              value={draft.benefits}
              onChange={(e) => update(draft.localId, { benefits: e.target.value })}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Sale start"
                type="datetime-local"
                hint="When this tier goes on sale. Blank = as soon as the event is live."
                value={draft.sale_start}
                onChange={(e) =>
                  update(draft.localId, { sale_start: e.target.value })
                }
              />
              <Input
                label="Sale end"
                type="datetime-local"
                hint="When sales for this tier stop."
                error={saleError ?? undefined}
                value={draft.sale_end}
                onChange={(e) =>
                  update(draft.localId, { sale_end: e.target.value })
                }
              />
            </div>
            <Input
              label="Access code"
              hint="Optional secret code for hidden or invite-only tiers."
              value={draft.access_code}
              onChange={(e) =>
                update(draft.localId, { access_code: e.target.value })
              }
            />
            {isTable ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <Textarea
                  label="Table perks"
                  rows={2}
                  hint="What the table package includes (bottle service, hostess, reserved seats)."
                  value={draft.table_perks}
                  onChange={(e) =>
                    update(draft.localId, { table_perks: e.target.value })
                  }
                />
                <Input
                  label="Reservation hold (minutes)"
                  type="number"
                  min={1}
                  hint="How long a pending table booking is held before release."
                  value={draft.reservation_hold_minutes}
                  onChange={(e) =>
                    update(draft.localId, {
                      reservation_hold_minutes: e.target.value,
                    })
                  }
                />
              </div>
            ) : null}
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">
                Transfer = buyer can pass the ticket. Refund = this tier can be
                refunded under your event policy. Waitlist = collect interest when
                sold out.
              </p>
              <div className="flex flex-wrap gap-4 text-sm text-foreground">
                <label className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={draft.transfer_allowed}
                    onChange={(e) =>
                      update(draft.localId, {
                        transfer_allowed: e.target.checked,
                      })
                    }
                  />
                  Transfer allowed
                </label>
                <label className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={draft.refund_allowed}
                    onChange={(e) =>
                      update(draft.localId, { refund_allowed: e.target.checked })
                    }
                  />
                  Refund allowed
                </label>
                <label className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={draft.waitlist_enabled}
                    onChange={(e) =>
                      update(draft.localId, {
                        waitlist_enabled: e.target.checked,
                      })
                    }
                  />
                  Waitlist enabled
                </label>
              </div>
            </div>
          </StudioItemCard>
        );
      })}
      {drafts.length > 0 ? (
        <Button
          type="button"
          variant="secondary"
          onClick={() => onChange([...drafts, newDraft()])}
        >
          Add ticket type
        </Button>
      ) : null}
    </div>
  );
}
