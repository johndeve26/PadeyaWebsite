"use client";

import { Input, Select, Textarea } from "@/components/ui";

import {
  REFUND_POLICY_TYPES,
  refundPolicyNeedsText,
} from "./policy-utils";
import { StudioFieldGroup, StudioMicrocopy } from "./studio-ui";

export function PolicySelector({
  values,
  onChange,
}: {
  values: {
    refund_policy_type: string;
    refund_policy_text: string;
    cancellation_policy: string;
    age_restriction: string;
    id_required: boolean;
    safety_notice: string;
    terms_acknowledgement: string;
    door_sales_allowed: boolean;
    open_ambassadors_enabled: boolean;
    open_ambassador_commission_percent: string;
    re_entry_allowed: boolean;
    check_in_start_time: string;
    check_in_end_time: string;
  };
  onChange: (key: string, value: string | boolean) => void;
}) {
  const needsRefundText = refundPolicyNeedsText(values.refund_policy_type);

  return (
    <div className="space-y-4">
      <StudioMicrocopy>
        Guests see these rules before they pay and at the door. Keep them clear —
        vague policies create support load.
      </StudioMicrocopy>

      <StudioFieldGroup
        title="Refunds & cancellation"
        description="How money and plans change if a guest cancels or you postpone."
      >
        <Select
          label="Refund policy type"
          hint="Pick the rule that matches how you handle money if a guest cancels."
          value={values.refund_policy_type}
          onChange={(e) => onChange("refund_policy_type", e.target.value)}
        >
          {REFUND_POLICY_TYPES.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Textarea
          label={
            needsRefundText
              ? "Refund policy details *"
              : "Refund policy details"
          }
          rows={3}
          hint={
            needsRefundText
              ? "Required for Custom and Partial refund only — explain fees, deadlines, and how to request."
              : "Optional plain-language notes (fees, deadlines, how to request)."
          }
          value={values.refund_policy_text}
          onChange={(e) => onChange("refund_policy_text", e.target.value)}
          error={
            needsRefundText && !values.refund_policy_text.trim()
              ? "Details required for this refund type"
              : undefined
          }
        />
        <Textarea
          label="Cancellation policy"
          rows={3}
          hint="What happens if you cancel or postpone the event (full refund, reschedule, credit, etc.)."
          value={values.cancellation_policy}
          onChange={(e) => onChange("cancellation_policy", e.target.value)}
        />
      </StudioFieldGroup>

      <StudioFieldGroup
        title="Guest requirements"
        description="Age, safety, and the line guests acknowledge at checkout."
      >
        <Input
          label="Age restriction"
          hint="Minimum age at the door (e.g. 18+ or 21+). Leave blank if all ages are welcome."
          value={values.age_restriction}
          onChange={(e) => onChange("age_restriction", e.target.value)}
          placeholder="18+"
        />
        <Textarea
          label="Safety notice"
          rows={2}
          hint="Anything guests should know about security, crowd size, or looking after themselves at the venue."
          value={values.safety_notice}
          onChange={(e) => onChange("safety_notice", e.target.value)}
        />
        <Textarea
          label="Terms acknowledgement"
          rows={2}
          hint="Short line guests agree to at checkout (e.g. “I confirm I meet the age and dress code rules”)."
          value={values.terms_acknowledgement}
          onChange={(e) => onChange("terms_acknowledgement", e.target.value)}
        />
      </StudioFieldGroup>

      <StudioFieldGroup
        title="Check-in window"
        description="When staff can scan tickets — often matches doors open."
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            label="Check-in start"
            type="datetime-local"
            hint="When scanning can begin."
            value={values.check_in_start_time}
            onChange={(e) => onChange("check_in_start_time", e.target.value)}
          />
          <Input
            label="Check-in end"
            type="datetime-local"
            hint="When scanning stops (e.g. late-entry cutoff)."
            value={values.check_in_end_time}
            onChange={(e) => onChange("check_in_end_time", e.target.value)}
          />
        </div>
      </StudioFieldGroup>

      <StudioFieldGroup
        title="Door rules"
        description="Tick what applies at the entrance so guests know before they arrive."
      >
        <div className="flex flex-wrap gap-4 text-sm text-foreground">
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={values.id_required}
              onChange={(e) => onChange("id_required", e.target.checked)}
            />
            ID required
          </label>
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={values.door_sales_allowed}
              onChange={(e) => onChange("door_sales_allowed", e.target.checked)}
            />
            Door sales allowed
          </label>
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={values.re_entry_allowed}
              onChange={(e) => onChange("re_entry_allowed", e.target.checked)}
            />
            Re-entry allowed
          </label>
        </div>
      </StudioFieldGroup>

      <StudioFieldGroup
        title="Event Ambassadors"
        description="Let any logged-in Pàdéyá user promote this event with a unique Ambassador link and earn commission on verified purchases."
      >
        <label className="inline-flex items-center gap-2 text-sm text-foreground">
          <input
            type="checkbox"
            checked={values.open_ambassadors_enabled}
            onChange={(e) => onChange("open_ambassadors_enabled", e.target.checked)}
          />
          Enable open Ambassadors
        </label>
        <Input
          label="Ambassador commission %"
          type="number"
          min={0}
          max={100}
          step="0.01"
          hint="Snapshotted when someone joins. Applies to verified paid orders attributed to their Ambassador code."
          value={values.open_ambassador_commission_percent}
          onChange={(e) =>
            onChange("open_ambassador_commission_percent", e.target.value)
          }
          disabled={!values.open_ambassadors_enabled}
        />
      </StudioFieldGroup>
    </div>
  );
}
