"use client";

import type { VaultItemEditorValues } from "@/components/vault/studio/VaultItemEditor";
import { VaultAccessRuleEditor } from "@/components/vault/studio/VaultAccessRuleEditor";
import { Input } from "@/components/ui";
import type { EventItem } from "@/lib/types/events";

type Props = {
  values: VaultItemEditorValues;
  onChange: (next: VaultItemEditorValues) => void;
  events: EventItem[];
};

export function AccessStep({ values, onChange, events }: Props) {
  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h2 className="text-xl font-extrabold text-foreground">Access</h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Server-side rules decide who unlocks this drop. Never trust the client
          for entitlement.
        </p>
      </div>

      <VaultAccessRuleEditor
        value={values.access}
        onChange={(access) => onChange({ ...values, access })}
        events={events}
      />

      <Input
        label="Drop expiry (optional)"
        type="datetime-local"
        value={values.expires_at}
        onChange={(e) => onChange({ ...values, expires_at: e.target.value })}
        hint="After this time the drop leaves the public catalog and unlocks stop. Separate from access start/end."
      />
    </div>
  );
}
