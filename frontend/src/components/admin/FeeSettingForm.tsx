"use client";

import { useMemo } from "react";

import { Button, Input, Select, Switch, Textarea } from "@/components/ui";
import {
  FEE_CATEGORY_OPTIONS,
  FEE_KEY_PRESETS,
  FEE_PAYER_OPTIONS,
  FEE_TYPE_OPTIONS,
  PAYER_COPY,
} from "@/lib/types/fees";

export type FeeFormState = {
  fee_key: string;
  label: string;
  category: string;
  fee_type: string;
  /** Percentage as entered (e.g. "5" or "2.5"). */
  percentage_value: string;
  /** Fixed major units (₦), converted to minor on submit. */
  fixed_value_major: string;
  currency: string;
  payer: string;
  enabled: boolean;
  applies_to: string;
  notes: string;
  effective_from: string;
  effective_to: string;
};

export const emptyFeeForm = (): FeeFormState => {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return {
    fee_key: "ticket_commission",
    label: "Ticket commission",
    category: "ticket",
    fee_type: "percentage",
    percentage_value: "5",
    fixed_value_major: "",
    currency: "NGN",
    payer: "host",
    enabled: true,
    applies_to: "all",
    notes: "",
    effective_from: now.toISOString().slice(0, 16),
    effective_to: "",
  };
};

type Props = {
  value: FeeFormState;
  onChange: (next: FeeFormState) => void;
  onSubmit: () => void;
  busy?: boolean;
  submitLabel?: string;
  /** When editing, fee_key is usually locked. */
  lockFeeKey?: boolean;
  readOnly?: boolean;
};

export function FeeSettingForm({
  value,
  onChange,
  onSubmit,
  busy = false,
  submitLabel = "Save fee",
  lockFeeKey = false,
  readOnly = false,
}: Props) {
  const showPct =
    value.fee_type === "percentage" || value.fee_type === "mixed";
  const showFixed = value.fee_type === "fixed" || value.fee_type === "mixed";

  const payerHint = useMemo(
    () => PAYER_COPY[value.payer] ?? "",
    [value.payer],
  );

  function patch(partial: Partial<FeeFormState>) {
    onChange({ ...value, ...partial });
  }

  function applyPreset(feeKey: string) {
    const preset = FEE_KEY_PRESETS.find((p) => p.fee_key === feeKey);
    if (!preset) {
      patch({ fee_key: feeKey });
      return;
    }
    patch({
      fee_key: preset.fee_key,
      label: preset.label,
      category: preset.category,
      fee_type: preset.fee_type,
      payer: preset.payer,
      percentage_value:
        preset.fee_type === "fixed" ? "" : value.percentage_value || "5",
      fixed_value_major:
        preset.fee_type === "percentage" ? "" : value.fixed_value_major || "100",
    });
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
        <Select
          label="Fee preset / key"
          value={value.fee_key}
          disabled={lockFeeKey || readOnly}
          onChange={(e) => applyPreset(e.target.value)}
        >
          {FEE_KEY_PRESETS.map((p) => (
            <option key={p.fee_key} value={p.fee_key}>
              {p.label} ({p.fee_key})
            </option>
          ))}
          {!FEE_KEY_PRESETS.some((p) => p.fee_key === value.fee_key) ? (
            <option value={value.fee_key}>{value.fee_key}</option>
          ) : null}
        </Select>
        <Input
          label="Fee name"
          value={value.label}
          disabled={readOnly}
          onChange={(e) => patch({ label: e.target.value })}
          required
        />
        <Select
          label="Category"
          value={value.category}
          disabled={readOnly}
          onChange={(e) => patch({ category: e.target.value })}
        >
          {FEE_CATEGORY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
        <Select
          label="Fee type"
          value={value.fee_type}
          disabled={readOnly}
          onChange={(e) => patch({ fee_type: e.target.value })}
        >
          {FEE_TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
        {showPct ? (
          <Input
            label="Percentage value"
            type="number"
            min={0}
            step="0.0001"
            value={value.percentage_value}
            disabled={readOnly}
            onChange={(e) => patch({ percentage_value: e.target.value })}
            hint="e.g. 5 for 5%"
            required={value.fee_type !== "fixed"}
          />
        ) : null}
        {showFixed ? (
          <Input
            label="Fixed value (₦)"
            type="number"
            min={0}
            step="0.01"
            value={value.fixed_value_major}
            disabled={readOnly}
            onChange={(e) => patch({ fixed_value_major: e.target.value })}
            hint="Stored as kobo on the server"
            required={value.fee_type !== "percentage"}
          />
        ) : null}
        <Input
          label="Currency"
          value={value.currency}
          disabled={readOnly}
          onChange={(e) => patch({ currency: e.target.value.toUpperCase() })}
        />
        <Select
          label="Payer"
          value={value.payer}
          disabled={readOnly}
          onChange={(e) => patch({ payer: e.target.value })}
          hint={payerHint}
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
        <Input
          label="Applies to"
          value={value.applies_to}
          disabled={readOnly}
          onChange={(e) => patch({ applies_to: e.target.value })}
        />
      </div>

      <Textarea
        label="Notes / internal reason"
        value={value.notes}
        disabled={readOnly}
        onChange={(e) => patch({ notes: e.target.value })}
        rows={3}
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

/** Convert form major fixed amount to minor units for API. */
export function fixedMajorToMinor(major: string): number | null {
  if (!major.trim()) return null;
  const n = Number(major);
  if (!Number.isFinite(n) || n < 0) return null;
  return Math.round(n * 100);
}

export function datetimeLocalToIso(value: string): string {
  if (!value) return new Date().toISOString();
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return new Date().toISOString();
  return d.toISOString();
}
