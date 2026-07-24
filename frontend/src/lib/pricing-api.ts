import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import type { PublicPricingResponse } from "@/lib/types/pricing";

export async function fetchPublicPricing(): Promise<PublicPricingResponse | null> {
  try {
    const base = getApiBaseUrl();
    const prefix = getApiPrefix();
    const res = await fetch(`${base}${prefix}/pricing/public`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    return (await res.json()) as PublicPricingResponse;
  } catch {
    return null;
  }
}
