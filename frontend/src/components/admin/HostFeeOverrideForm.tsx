"use client";

import { Button, Input, Select, Switch, Textarea } from "@/components/ui";
import {
  FEE_KEY_PRESETS,
  FEE_PAYER_OPTIONS,
  PAYER_COPY,
} from "@/lib/types/fees";

export type OverrideFormState = {
  host_id: string;
  fee_key: string;
  percentage_value: string;
  fixed_value_major: string;
  payer: string;
  enabled: boolean;
  effective_from: string;
  effective_to: string;
  reason: string;
};

export function emptyOverrideForm(hostId = ""): OverrideFormState {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return {
    host_id: hostId,
    fee_key: "ticket_commission",
    percentage_value: "3",
    fixed_value_major: "",
    payer: "host",
    enabled: true,
    effective_from: now.toISOString().slice(0, 16),
    effective_to: "",
    reason: "",
  };
}

type Props = {
  value: OverrideFormState;
  onChange: (next: OverrideFormState) => void;
  onSubmit: () => void;
  busy?: boolean;
  submitLabel?: string;
  lockHostId?: boolean;
  readOnly?: boolean;
};

export function HostFeeOverrideForm({
  value,
  onChange,
  onSubmit,
  busy = false,
  submitLabel = "Save override",
  lockHostId = false,
  readOnly = false,
}: Props) {
  function patch(partial: Partial<OverrideFormState>) {
    onChange({ ...value, ...partial });
  }

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (!readOnly) onSubmit();
      }}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          label="Host ID"
          value={value.host_id}
          disabled={lockHostId || readOnly}
          onChange={(e) => patch({ host_id: e.target.value })}
          required
        />
        <Select
          label="Fee key"
          value={value.fee_key}
          disabled={readOnly}
          onChange={(e) => patch({ fee_key: e.target.value })}
        >
          {FEE_KEY_PRESETS.map((p) => (
            <option key={p.fee_key} value={p.fee_key}>
              {p.label}
            </option>
          ))}
        </Select>
        <Input
          label="Percentage value"
          type="number"
          min={0}
          step="0.0001"
          value={value.percentage_value}
          disabled={readOnly}
          onChange={(e) => patch({ percentage_value: e.target.value })}
          hint="Leave blank to inherit percentage from global"
        />
        <Input
          label="Fixed value (₦)"
          type="number"
          min={0}
          step="0.01"
          value={value.fixed_value_major}
          disabled={readOnly}
          onChange={(e) => patch({ fixed_value_major: e.target.value })}
          hint="Leave blank to inherit fixed from global"
        />
        <Select
          label="Payer"
          value={value.payer}
          disabled={readOnly}
          onChange={(e) => patch({ payer: e.target.value })}
          hint={PAYER_COPY[value.payer]}
        >
          {FEE_PAYER_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
        <Input
          label="Effective from"
          type="datetime-local"
          value={value.effective_from}
          disabled={readOnly}
          onChange={(e) => patch({ effective_from: e.target.value })}
          required
        />
        <Input
          label="Effective to (optional)"
          type="datetime-local"
          value={value.effective_to}
          disabled={readOnly}
          onChange={(e) => patch({ effective_to: e.target.value })}
        />
      </div>
      <Textarea
        label="Reason"
        value={value.reason}
        disabled={readOnly}
        onChange={(e) => patch({ reason: e.target.value })}
        rows={3}
        hint="Internal note for why this host has a special rate"
      />
      <Switch
        label="Enabled"
        checked={value.enabled}
        disabled={readOnly}
        onCheckedChange={(checked) => patch({ enabled: checked })}
      />
      {!readOnly ? (
        <Button type="submit" disabled={busy}>
          {busy ? "Saving…" : submitLabel}
        </Button>
      ) : null}
    </form>
  );
}
