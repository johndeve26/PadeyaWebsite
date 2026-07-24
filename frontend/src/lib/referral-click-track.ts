import { getOrCreateAnonymousId } from "@/lib/analytics-client";
import { trackReferralClick } from "@/lib/promos-api";

export type ReferralClickSource =
  | "event_page"
  | "merch_page"
  | "host_page"
  | "campaign_link"
  | "checkout";

/** Canonical client helper for ambassador referral landing clicks. */
export function trackAmbassadorReferralLanding(input: {
  referral_code: string;
  event_id?: string;
  landing_path?: string;
  source: ReferralClickSource;
}): void {
  void trackReferralClick({
    referral_code: input.referral_code,
    event_id: input.event_id,
    landing_path: input.landing_path,
    source: input.source,
    anonymous_visitor_id: getOrCreateAnonymousId(),
  }).catch(() => undefined);
}
