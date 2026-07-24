export type OrderItem = {
  id: string;
  item_kind?: "ticket" | "merch" | string;
  ticket_type_id?: string | null;
  ticket_type_name?: string | null;
  merch_product_id?: string | null;
  merch_variant_id?: string | null;
  product_name?: string | null;
  variant_label?: string | null;
  quantity: number;
  unit_price: string | number;
  line_total: string | number;
  fulfillment_status?: string | null;
  pickup_code?: string | null;
  pickup_instructions?: string | null;
};

export type OrderMerchFulfillment = {
  id: string;
  order_item_id: string;
  status: string;
  pickup_code: string;
  pickup_instructions_snapshot?: string | null;
  product_name_snapshot: string;
  variant_label_snapshot: string;
  quantity: number;
  fulfilled_at?: string | null;
};

export type OrderCheckoutAnswer = {
  id: string;
  question_id?: string | null;
  question_label: string;
  question_type: string;
  value: string;
};

export type Payment = {
  id: string;
  provider: string;
  reference: string;
  amount: string | number;
  currency: string;
  status: string;
  authorization_url?: string | null;
  paid_at?: string | null;
  created_at: string;
};

export type Order = {
  id: string;
  reference: string;
  event_id: string;
  status: string;
  currency: string;
  subtotal_amount: string | number;
  discount_amount?: string | number;
  merch_discount_amount?: string | number;
  shipping_amount?: string | number;
  buyer_fee_total?: string | number;
  host_fee_total?: string | number;
  processing_fee_total?: string | number;
  platform_revenue_total?: string | number;
  host_net_estimate?: string | number;
  discount_total?: string | number;
  final_total?: string | number;
  fee_breakdown?: OrderFeeBreakdownLine[];
  total_amount: string | number;
  promo_code_snapshot?: string | null;
  merch_discount_code_snapshot?: string | null;
  referral_code?: string | null;
  fulfillment_method?: string | null;
  buyer_email: string;
  buyer_name: string;
  purchase_mode?: string;
  is_gift?: boolean;
  purchased_for_someone_else?: boolean;
  gift_message?: string | null;
  send_ticket_to_recipient?: boolean;
  keep_buyer_copy?: boolean;
  recipient_name?: string | null;
  recipient_email?: string | null;
  recipient_phone?: string | null;
  created_at: string;
  paid_at: string | null;
  items: OrderItem[];
  payments: Payment[];
  checkout_answers?: OrderCheckoutAnswer[];
  attendees?: {
    id: string;
    ticket_type_id: string;
    unit_index: number;
    attendee_name: string;
    attendee_email: string;
    attendee_phone?: string | null;
    delivery_email?: string | null;
    delivery_phone?: string | null;
  }[];
  event_title?: string | null;
  event_slug?: string | null;
  host_id?: string | null;
  host_name?: string | null;
  host_slug?: string | null;
  merch_fulfillments?: OrderMerchFulfillment[];
};

export type OrderFeeBreakdownLine = {
  fee_key: string;
  label: string;
  payer: string;
  amount: string | number;
  currency?: string;
};

export type BuyerFeeQuote = {
  subtotal: string | number;
  discount_total: string | number;
  shipping_amount: string | number;
  buyer_fee_total: string | number;
  processing_fee_total: string | number;
  final_total: string | number;
  fee_breakdown: OrderFeeBreakdownLine[];
};

export type CheckoutResult = {
  order_id: string;
  reference: string;
  amount: string | number;
  currency: string;
  free_checkout: boolean;
  authorization_url?: string | null;
  access_code?: string | null;
  public_key?: string | null;
  paystack_mode?: "test" | "live" | null;
  paystack_customer_email?: string | null;
  buyer_fee_total?: string | number;
  final_total?: string | number;
  fee_breakdown?: OrderFeeBreakdownLine[];
};

export type Ticket = {
  id: string;
  public_code: string;
  event_id: string;
  order_id: string;
  ticket_type_id: string;
  ticket_type_name: string;
  status: string;
  holder_name: string;
  holder_email: string;
  holder_phone?: string | null;
  is_gift?: boolean;
  created_at: string;
  checked_in_at?: string | null;
  event_title?: string | null;
  event_slug?: string | null;
  event_cover_url?: string | null;
  event_starts_at?: string | null;
  event_ends_at?: string | null;
  event_status?: string | null;
  host_id?: string | null;
  host_name?: string | null;
  host_username?: string | null;
  location_label?: string | null;
  qr_payload?: string | null;
  qr_mode?: string;
  device_bound?: boolean;
  seat_label?: string | null;
  table_label?: string | null;
  attendee_index?: number | null;
  qr_expires_at?: string | null;
  qr_rotation_version?: number | null;
  linked_merch?: {
    id: string;
    order_item_id: string;
    product_name: string;
    variant_label: string;
    quantity: number;
    status: string;
    display_status?: string | null;
    pickup_code: string;
    pickup_instructions?: string | null;
  }[];
};
