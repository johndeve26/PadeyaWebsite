"use client";

import { Input, Textarea } from "@/components/ui";
import type { LegacyContactSettings } from "@/lib/types/legacy";

type Props = {
  value: LegacyContactSettings;
  onChange: (next: LegacyContactSettings) => void;
};

export function LegacyContactSettingsEditor({ value, onChange }: Props) {
  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-base font-extrabold text-foreground">Contact preference</h3>
        <p className="text-sm text-muted-foreground">
          How brands and fans should reach you from Legacy.
        </p>
      </div>
      <label className="block space-y-1.5 text-sm font-semibold text-foreground">
        Preference
        <select
          className="w-full rounded-[var(--radius-md)] border border-input-border bg-input-background px-3 py-2 text-sm text-input-foreground"
          value={value.preference}
          onChange={(e) => onChange({ ...value, preference: e.target.value })}
        >
          <option value="none">Hidden</option>
          <option value="email">Public email</option>
          <option value="form">Contact form note</option>
          <option value="email_and_form">Email + note</option>
          <option value="social">Prefer social</option>
        </select>
      </label>
      <label className="block space-y-1.5 text-sm font-semibold text-foreground">
        Public email
        <Input
          value={value.public_email ?? ""}
          onChange={(e) => onChange({ ...value, public_email: e.target.value || null })}
          placeholder="bookings@example.com"
        />
      </label>
      <label className="block space-y-1.5 text-sm font-semibold text-foreground">
        Preferred channel
        <Input
          value={value.preferred_channel ?? ""}
          onChange={(e) =>
            onChange({ ...value, preferred_channel: e.target.value || null })
          }
          placeholder="Instagram DM, email, WhatsApp…"
        />
      </label>
      <label className="block space-y-1.5 text-sm font-semibold text-foreground">
        Contact note
        <Textarea
          rows={3}
          value={value.note ?? ""}
          onChange={(e) => onChange({ ...value, note: e.target.value || null })}
          placeholder="Best for brand partnerships and press."
        />
      </label>
      <label className="flex items-center gap-2 text-sm font-semibold text-foreground">
        <input
          type="checkbox"
          checked={value.show_contact_form}
          onChange={(e) => onChange({ ...value, show_contact_form: e.target.checked })}
        />
        Show contact form CTA
      </label>
    </div>
  );
}
