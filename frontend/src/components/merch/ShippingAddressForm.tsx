"use client";

import { Input, Textarea } from "@/components/ui";

export type ShippingAddressValues = {
  recipient_name: string;
  phone_number: string;
  address_line_1: string;
  address_line_2: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  delivery_notes: string;
};

type Props = {
  value: ShippingAddressValues;
  onChange: (next: ShippingAddressValues) => void;
  disabled?: boolean;
};

const empty: ShippingAddressValues = {
  recipient_name: "",
  phone_number: "",
  address_line_1: "",
  address_line_2: "",
  city: "",
  state: "",
  country: "Nigeria",
  postal_code: "",
  delivery_notes: "",
};

export function emptyShippingAddress(): ShippingAddressValues {
  return { ...empty };
}

/** Map form values to `POST /orders` shipping_address (backend aliases accepted). */
export function shippingAddressToApiPayload(value: ShippingAddressValues) {
  return {
    recipient_name: value.recipient_name.trim(),
    phone: value.phone_number.trim(),
    phone_number: value.phone_number.trim(),
    line1: value.address_line_1.trim(),
    address_line_1: value.address_line_1.trim(),
    line2: value.address_line_2.trim() || null,
    address_line_2: value.address_line_2.trim() || null,
    city: value.city.trim(),
    state: value.state.trim(),
    country: value.country.trim(),
    postal_code: value.postal_code.trim() || null,
    notes: value.delivery_notes.trim() || null,
    delivery_notes: value.delivery_notes.trim() || null,
  };
}

export function isShippingAddressComplete(value: ShippingAddressValues): boolean {
  return Boolean(
    value.recipient_name.trim() &&
      value.phone_number.trim().length >= 7 &&
      value.address_line_1.trim() &&
      value.city.trim() &&
      value.state.trim() &&
      value.country.trim(),
  );
}

/** Private shipping fields for checkout — never shown publicly after submit. */
export function ShippingAddressForm({ value, onChange, disabled }: Props) {
  const set = (key: keyof ShippingAddressValues, v: string) =>
    onChange({ ...value, [key]: v });

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold text-foreground">Delivery address</p>
      <p className="text-xs text-muted-foreground">
        Kept private on Pàdéyá — only used for your merch delivery.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5 sm:col-span-2">
          <label
            htmlFor="ship-name"
            className="text-xs font-bold uppercase tracking-wide text-muted-foreground"
          >
            Recipient name
          </label>
          <Input
            id="ship-name"
            value={value.recipient_name}
            disabled={disabled}
            onChange={(e) => set("recipient_name", e.target.value)}
            autoComplete="name"
            required
          />
        </div>
        <div className="space-y-1.5">
          <label
            htmlFor="ship-phone"
            className="text-xs font-bold uppercase tracking-wide text-muted-foreground"
          >
            Phone number
          </label>
          <Input
            id="ship-phone"
            type="tel"
            value={value.phone_number}
            disabled={disabled}
            onChange={(e) => set("phone_number", e.target.value)}
            autoComplete="tel"
            required
          />
        </div>
        <div className="space-y-1.5">
          <label
            htmlFor="ship-country"
            className="text-xs font-bold uppercase tracking-wide text-muted-foreground"
          >
            Country
          </label>
          <Input
            id="ship-country"
            value={value.country}
            disabled={disabled}
            onChange={(e) => set("country", e.target.value)}
            autoComplete="country-name"
            required
          />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <label
            htmlFor="ship-line1"
            className="text-xs font-bold uppercase tracking-wide text-muted-foreground"
          >
            Address line 1
          </label>
          <Input
            id="ship-line1"
            value={value.address_line_1}
            disabled={disabled}
            onChange={(e) => set("address_line_1", e.target.value)}
            autoComplete="address-line1"
            required
          />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <label
            htmlFor="ship-line2"
            className="text-xs font-bold uppercase tracking-wide text-muted-foreground"
          >
            Address line 2
          </label>
          <Input
            id="ship-line2"
            value={value.address_line_2}
            disabled={disabled}
            onChange={(e) => set("address_line_2", e.target.value)}
            autoComplete="address-line2"
          />
        </div>
        <div className="space-y-1.5">
          <label
            htmlFor="ship-city"
            className="text-xs font-bold uppercase tracking-wide text-muted-foreground"
          >
            City
          </label>
          <Input
            id="ship-city"
            value={value.city}
            disabled={disabled}
            onChange={(e) => set("city", e.target.value)}
            autoComplete="address-level2"
            required
          />
        </div>
        <div className="space-y-1.5">
          <label
            htmlFor="ship-state"
            className="text-xs font-bold uppercase tracking-wide text-muted-foreground"
          >
            State
          </label>
          <Input
            id="ship-state"
            value={value.state}
            disabled={disabled}
            onChange={(e) => set("state", e.target.value)}
            autoComplete="address-level1"
            required
          />
        </div>
        <div className="space-y-1.5">
          <label
            htmlFor="ship-postal"
            className="text-xs font-bold uppercase tracking-wide text-muted-foreground"
          >
            Postal code
          </label>
          <Input
            id="ship-postal"
            value={value.postal_code}
            disabled={disabled}
            onChange={(e) => set("postal_code", e.target.value)}
            autoComplete="postal-code"
          />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <label
            htmlFor="ship-notes"
            className="text-xs font-bold uppercase tracking-wide text-muted-foreground"
          >
            Delivery notes
          </label>
          <Textarea
            id="ship-notes"
            rows={2}
            value={value.delivery_notes}
            disabled={disabled}
            onChange={(e) => set("delivery_notes", e.target.value)}
            placeholder="Gate code, landmark, preferred time…"
          />
        </div>
      </div>
    </div>
  );
}
