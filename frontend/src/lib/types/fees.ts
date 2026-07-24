/** Platform fee settings and host fee overrides (admin finance). */

export type FeeCategory =
  | "ticket"
  | "merch"
  | "vault"
  | "payment"
  | "refund"
  | "sponsorship"
  | "general";

export type FeeType = "percentage" | "fixed" | "mixed";

export type FeePayer = "buyer" | "host" | "platform";

export type PlatformFeeSetting = {
  id: string;
  fee_key: string;
  label: string;
  category: FeeCategory | string;
  fee_type: FeeType | string;
  percentage_value: string | number | null;
  /** Integer minor units (kobo for NGN). */
  fixed_value: number | null;
  currency: string;
  payer: FeePayer | string;
  enabled: boolean;
  applies_to: string;
  notes: string | null;
  effective_from: string;
  effective_to: string | null;
  created_by_admin_id: string | null;
  updated_by_admin_id: string | null;
  created_at: string;
  updated_at: string;
};

export type PlatformFeeSettingCreate = {
  fee_key: string;
  label: string;
  category: string;
  fee_type: string;
  percentage_value?: string | number | null;
  fixed_value?: number | null;
  currency?: string;
  payer: string;
  enabled?: boolean;
  applies_to?: string;
  notes?: string | null;
  effective_from: string;
  effective_to?: string | null;
};

export type PlatformFeeSettingUpdate = {
  label?: string;
  fee_type?: string;
  percentage_value?: string | number | null;
  fixed_value?: number | null;
  currency?: string;
  payer?: string;
  enabled?: boolean;
  applies_to?: string;
  notes?: string | null;
  effective_from?: string;
  effective_to?: string | null;
};

export type HostFeeOverride = {
  id: string;
  host_id: string;
  fee_key: string;
  percentage_value: string | number | null;
  fixed_value: number | null;
  payer: FeePayer | string;
  enabled: boolean;
  effective_from: string;
  effective_to: string | null;
  reason: string | null;
  created_by_admin_id: string | null;
  updated_by_admin_id: string | null;
  created_at: string;
  updated_at: string;
};

export type HostFeeOverrideCreate = {
  host_id: string;
  fee_key: string;
  percentage_value?: string | number | null;
  fixed_value?: number | null;
  payer: string;
  enabled?: boolean;
  effective_from: string;
  effective_to?: string | null;
  reason?: string | null;
};

export type HostFeeOverrideUpdate = {
  percentage_value?: string | number | null;
  fixed_value?: number | null;
  payer?: string;
  enabled?: boolean;
  effective_from?: string;
  effective_to?: string | null;
  reason?: string | null;
};

export const FEE_CATEGORY_OPTIONS = [
  { value: "ticket", label: "Ticket" },
  { value: "merch", label: "Merch" },
  { value: "vault", label: "Vault" },
  { value: "payment", label: "Payment" },
  { value: "refund", label: "Refund" },
  { value: "sponsorship", label: "Sponsorship" },
  { value: "general", label: "General" },
] as const;

export const FEE_TYPE_OPTIONS = [
  { value: "percentage", label: "Percentage" },
  { value: "fixed", label: "Fixed" },
  { value: "mixed", label: "Mixed (percentage + fixed)" },
] as const;

export const FEE_PAYER_OPTIONS = [
  { value: "buyer", label: "Buyer pays" },
  { value: "host", label: "Host pays" },
  { value: "platform", label: "Platform absorbs" },
] as const;

/** Preset fee keys matching backend catalog. */
export const FEE_KEY_PRESETS = [
  {
    fee_key: "ticket_commission",
    label: "Ticket commission",
    category: "ticket",
    fee_type: "percentage",
    payer: "host",
  },
  {
    fee_key: "ticket_fixed_fee",
    label: "Ticket fixed fee",
    category: "ticket",
    fee_type: "fixed",
    payer: "host",
  },
  {
    fee_key: "buyer_service_fee",
    label: "Buyer platform / service fee",
    category: "general",
    fee_type: "mixed",
    payer: "buyer",
  },
  {
    fee_key: "merch_commission",
    label: "Merch commission",
    category: "merch",
    fee_type: "percentage",
    payer: "host",
  },
  {
    fee_key: "merch_fixed_fee",
    label: "Merch fixed fee",
    category: "merch",
    fee_type: "fixed",
    payer: "host",
  },
  {
    fee_key: "vault_commission",
    label: "Vault commission",
    category: "vault",
    fee_type: "percentage",
    payer: "host",
  },
  {
    fee_key: "vault_fixed_fee",
    label: "Vault fixed fee",
    category: "vault",
    fee_type: "fixed",
    payer: "host",
  },
  {
    fee_key: "payment_processing_fee",
    label: "Payment / fiat processing fee",
    category: "payment",
    fee_type: "percentage",
    payer: "buyer",
  },
  {
    fee_key: "refund_fee",
    label: "Refund fee",
    category: "refund",
    fee_type: "fixed",
    payer: "buyer",
  },
] as const;

export const PAYER_COPY: Record<string, string> = {
  buyer: "Buyer platform fee is paid by the buyer.",
  host: "Host commission is deducted from host earnings.",
  platform: "Platform-absorbed fees reduce platform margin.",
};

/** Shared admin/host help copy for fee messaging. */
export const FEE_HELP_COPY = [
  "Buyer platform fee is paid by the buyer.",
  "Host commission is deducted from host earnings.",
  "Fee settings can differ by host.",
  "Order fee snapshots preserve the fee terms used at the time of sale.",
] as const;
