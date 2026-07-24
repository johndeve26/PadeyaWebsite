import Link from "next/link";

import { MarketingAudienceHero } from "@/components/marketing/MarketingAudienceHero";
import { MarketingFinalCta } from "@/components/marketing/MarketingFinalCta";

import { MerchFansSection } from "./MerchFansSection";
import { MerchFaqSection } from "./MerchFaqSection";
import { MerchFeesSection } from "./MerchFeesSection";
import { MerchFormatsSection } from "./MerchFormatsSection";
import { MerchHostsSection } from "./MerchHostsSection";
import { MerchHowItWorksSection } from "./MerchHowItWorksSection";
import { MerchNotificationsSection } from "./MerchNotificationsSection";
import { MerchPoliciesSection } from "./MerchPoliciesSection";
import { MerchWhereSection } from "./MerchWhereSection";
import { merchFinalCta, merchHero } from "./content";

export function MerchView() {
  return (
    <main className="min-w-0 overflow-x-clip pb-2">
      <MarketingAudienceHero
        eyebrow={merchHero.eyebrow}
        headline={merchHero.headline}
        support={merchHero.support}
        trustLine={merchHero.trustLine}
        primary={merchHero.primary}
        secondary={merchHero.secondary}
        tertiary={
          <p className="text-sm text-paper/55">
            <Link
              href="#how-it-works"
              className="font-semibold text-primary hover:underline"
            >
              Learn how merch works
            </Link>
            {" · "}
            <Link
              href="/for-hosts"
              className="font-semibold text-primary hover:underline"
            >
              For hosts
            </Link>
            {" · "}
            <Link href="/help" className="font-semibold text-primary hover:underline">
              Help
            </Link>
          </p>
        }
      />

      <MerchFansSection />
      <MerchHostsSection />
      <MerchFormatsSection />
      <MerchHowItWorksSection />
      <MerchWhereSection />
      <MerchNotificationsSection />
      <MerchFeesSection />
      <MerchPoliciesSection />
      <MerchFaqSection />

      <MarketingFinalCta
        title={merchFinalCta.title}
        description={merchFinalCta.description}
        primary={merchFinalCta.primary}
        secondary={merchFinalCta.secondary}
        tertiary={merchFinalCta.tertiary}
      />
    </main>
  );
}
