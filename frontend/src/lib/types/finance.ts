export type RefundRequest = {
  id: string;
  order_id: string;
  payment_id: string | null;
  buyer_user_id: string;
  host_id: string;
  event_id: string;
  status: string;
  refund_type: string;
  requested_amount: string | number;
  currency: string;
  reason: string;
  policy_snapshot: string;
  ticket_ids: string[] | null;
  escalation_note: string | null;
  review_note: string | null;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  created_at: string;
  order_reference: string | null;
  event_title: string | null;
};

export type HostBalance = {
  host_id: string;
  currency: string;
  available_balance: string | number;
  pending_payout_balance: string | number;
  lifetime_earned: string | number;
  lifetime_refunded: string | number;
  lifetime_paid_out: string | number;
  updated_at: string;
};

export type LedgerEntry = {
  id: string;
  host_id: string;
  entry_type: string;
  direction: string;
  amount: string | number;
  currency: string;
  available_balance_after: string | number;
  pending_payout_balance_after: string | number;
  reference_type: string | null;
  reference_id: string | null;
  description: string | null;
  created_by_user_id: string | null;
  created_at: string;
};

export type PayoutEvidence = {
  id: string;
  payout_request_id: string;
  bank_transfer_reference: string;
  evidence_file_url: string;
  admin_note: string | null;
  paid_at: string;
  paid_by_user_id: string;
  recipient_bank_snapshot: Record<string, string>;
  created_at: string;
};

export type PayoutRequest = {
  id: string;
  host_id: string;
  amount: string | number;
  currency: string;
  status: string;
  recipient_bank_snapshot: Record<string, string>;
  host_note: string | null;
  review_note: string | null;
  rejection_reason: string | null;
  requested_by_user_id: string;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  created_at: string;
  host_display_name: string | null;
  evidence: PayoutEvidence | null;
};

export type SettlementReport = {
  host_id: string | null;
  currency: string;
  total_earned: string | number;
  total_refunded: string | number;
  total_paid_out: string | number;
  available_balance: string | number;
  pending_payout_balance: string | number;
  open_refund_requests: number;
  open_payout_requests: number;
  ledger_entry_count: number;
};

export type HostFeeTerm = {
  fee_key: string;
  label: string;
  category: string;
  fee_type: string;
  percentage_value?: string | number | null;
  fixed_value_major?: string | number | null;
  currency: string;
  payer: string;
  source: string;
  enabled: boolean;
};

export type EarningsOrderRow = {
  row_kind: string;
  order_id?: string | null;
  reference: string;
  event_id?: string | null;
  event_title?: string | null;
  item_label: string;
  paid_at?: string | null;
  payment_status: string;
  payout_status: string;
  buyer_paid_total: string | number;
  item_subtotal: string | number;
  discount_total: string | number;
  shipping_amount?: string | number;
  host_gross: string | number;
  buyer_fee_total: string | number;
  host_fee_total: string | number;
  processing_fee_host?: string | number;
  ambassador_reward?: string | number;
  refund_amount: string | number;
  platform_revenue: string | number;
  host_net: string | number;
};

export type EarningsSummary = {
  host_id: string;
  host_display_name?: string | null;
  event_id?: string | null;
  event_title?: string | null;
  currency: string;
  gross_ticket_sales: string | number;
  gross_merch_sales: string | number;
  gross_vault_sales: string | number;
  discounts_total: string | number;
  shipping_total: string | number;
  host_gross: string | number;
  padeya_commission: string | number;
  processing_fees_host_paid: string | number;
  other_host_paid_fees: string | number;
  ambassador_rewards: string | number;
  refunds_total: string | number;
  deductions_total: string | number;
  buyer_platform_fees: string | number;
  platform_revenue_total: string | number;
  net_earnings: string | number;
  pending_payout: string | number;
  paid_out: string | number;
  available_balance: string | number;
  paid_order_count: number;
  vault_sale_count: number;
};

export type HostEarningsReport = {
  summary: EarningsSummary;
  fee_terms: HostFeeTerm[];
  rows: EarningsOrderRow[];
  note: string;
};

export type AdminHostEarningsOverviewRow = {
  host_id: string;
  host_display_name: string;
  currency: string;
  net_earnings: string | number;
  refunds_total: string | number;
  pending_payout: string | number;
  paid_out: string | number;
  available_balance: string | number;
};

export type PlatformRevenueSummary = {
  currency: string;
  gross_payment_volume: string | number;
  platform_revenue: string | number;
  ticket_commission_revenue: string | number;
  buyer_service_fee_revenue: string | number;
  merch_commission_revenue: string | number;
  vault_commission_revenue: string | number;
  processing_fee_revenue?: string | number;
  ticket_revenue?: string | number;
  merch_revenue?: string | number;
  vault_revenue?: string | number;
  refunds: string | number;
  ambassador_rewards?: string | number;
  host_net_payable: string | number;
  payouts_completed: string | number;
  pending_payouts: string | number;
  open_payout_requests?: number;
  entry_count?: number;
};

export type PlatformLedgerEntryRow = {
  id: string;
  entry_type: string;
  direction: string;
  amount: string | number;
  currency: string;
  order_id?: string | null;
  host_id?: string | null;
  event_id?: string | null;
  description?: string | null;
  reference_type?: string | null;
  reference_id?: string | null;
  payment_reference_masked?: string | null;
  category?: string | null;
  created_at: string;
};

export type PlatformRevenueReport = {
  summary: PlatformRevenueSummary;
  filters: Record<string, string | null | undefined>;
  entries: PlatformLedgerEntryRow[];
};
