"use client";

import { Input, Select, Textarea } from "@/components/ui";
import type { LegacyContactSettings } from "@/lib/types/legacy";

type Props = {
  value: LegacyContactSettings;
  onChange: (next: LegacyContactSettings) => void;
};

export function LegacyContactSettingsEditor({ value, onChange }: Props) {
  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-base font-extrabold text-foreground">Contact on Legacy</h3>
        <p className="text-sm text-muted-foreground">
          How brands and fans should reach you from your public page.
        </p>
      </div>
      <Select
        label="How people can reach you"
        value={value.preference}
        onChange={(e) => onChange({ ...value, preference: e.target.value })}
        hint="Controls what appears in your contact section."
      >
        <option value="none">Hidden — don’t show contact</option>
        <option value="email">Show a public email</option>
        <option value="form">Show a contact note only</option>
        <option value="email_and_form">Email + contact note</option>
        <option value="social">Point people to social links</option>
      </Select>
      <Input
        label="Public email"
        value={value.public_email ?? ""}
        onChange={(e) => onChange({ ...value, public_email: e.target.value || null })}
        placeholder="bookings@example.com"
        hint="Visible when preference includes email."
      />
      <Input
        label="Preferred channel"
        value={value.preferred_channel ?? ""}
        onChange={(e) =>
          onChange({ ...value, preferred_channel: e.target.value || null })
        }
        placeholder="Instagram DM, email, WhatsApp…"
        hint="Optional tip shown next to contact (e.g. “DM on Instagram”)."
      />
      <Textarea
        label="Contact note"
        rows={3}
        value={value.note ?? ""}
        onChange={(e) => onChange({ ...value, note: e.target.value || null })}
        placeholder="Best for brand partnerships and press. Reply within 48 hours."
        hint="Short instructions for people reaching out."
      />
      <label className="flex items-start gap-2 text-sm font-semibold text-foreground">
        <input
          type="checkbox"
          className="mt-0.5"
          checked={value.show_contact_form}
          onChange={(e) => onChange({ ...value, show_contact_form: e.target.checked })}
        />
        <span>
          Show a “Contact” button
          <span className="mt-0.5 block font-normal text-muted-foreground">
            Adds a contact CTA that scrolls to this section on your Legacy Page.
          </span>
        </span>
      </label>
    </div>
  );
}
