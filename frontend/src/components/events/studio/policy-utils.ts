/** Refund policy types accepted by Event Studio and the API. */
export const REFUND_POLICY_TYPES = [
  { value: "no_refunds", label: "No refunds" },
  {
    value: "refund_until_7_days_before",
    label: "Refund until 7 days before",
  },
  {
    value: "refund_until_24_hours_before",
    label: "Refund until 24 hours before",
  },
  { value: "partial_refund_only", label: "Partial refund only" },
  { value: "cancelled_event_only", label: "Cancelled event only" },
  { value: "admin_controlled", label: "Admin controlled" },
  { value: "custom", label: "Custom" },
] as const;

export type RefundPolicyType = (typeof REFUND_POLICY_TYPES)[number]["value"];

const TYPES_NEEDING_TEXT = new Set<string>([
  "custom",
  "partial_refund_only",
]);

export function refundPolicyLabel(type: string | null | undefined): string {
  if (!type) return "Standard Pàdéyá refund rules";
  const match = REFUND_POLICY_TYPES.find((opt) => opt.value === type);
  if (match) return match.label;
  return type.replaceAll("_", " ");
}

export function refundPolicyNeedsText(type: string | null | undefined): boolean {
  return Boolean(type && TYPES_NEEDING_TEXT.has(type));
}

/** Returns an error message, or null if policies look valid. */
export function policyFieldsError(values: {
  refund_policy_type: string;
  refund_policy_text: string;
  check_in_start_time: string;
  check_in_end_time: string;
}): string | null {
  if (
    refundPolicyNeedsText(values.refund_policy_type) &&
    !values.refund_policy_text.trim()
  ) {
    return "Add refund policy details when using Custom or Partial refund only.";
  }
  if (
    values.check_in_start_time &&
    values.check_in_end_time &&
    new Date(values.check_in_end_time) <= new Date(values.check_in_start_time)
  ) {
    return "Check-in end must be after check-in start.";
  }
  return null;
}
