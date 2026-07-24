/** Public-safe pricing payload from GET /api/v1/pricing/public */

export type PublicPricingFeeRow = {
  fee_key: string;
  label: string;
  category: string;
  payer: string;
  fee_type: string | null;
  public_description: string;
  appears_at: string[];
  configurable: boolean;
  may_vary_by_host: boolean;
  rates_public: boolean;
  enabled: boolean;
  percentage_value: string | number | null;
  fixed_value_major: string | number | null;
  currency: string;
  display_rate: string | null;
};

export type PublicPricingResponse = {
  currency: string;
  note: string;
  fees: PublicPricingFeeRow[];
  categories: PublicPricingFeeRow[];
};
