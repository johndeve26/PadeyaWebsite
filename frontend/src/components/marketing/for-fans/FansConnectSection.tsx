import Link from "next/link";

import { MarketingFeatureGrid } from "@/components/marketing/MarketingFeatureGrid";
import { MarketingSection } from "@/components/marketing/MarketingSection";
import { Button } from "@/components/ui";

import { forFansConnect } from "./content";

export function FansConnectSection() {
  return (
    <MarketingSection
      id="fan-connect"
      tone="muted"
      eyebrow="Fan Connect"
      title="Meet people around the same nights"
      description="Optional connections with privacy-safe discovery, messaging controls, and report/block tools, on your terms."
      headerAction={
        <Link href="/connect" className="hidden sm:inline-flex">
          <Button variant="secondary" size="lg">
            Open Fan Connect
          </Button>
        </Link>
      }
    >
      <MarketingFeatureGrid
        items={forFansConnect}
        columns={2}
        density="pillars"
      />
      <p className="text-sm text-muted-foreground">
        Manage who can reach you in{" "}
        <Link
          href="/connect/settings"
          className="font-semibold text-primary-text hover:underline"
        >
          Connect settings
        </Link>
        .
      </p>
    </MarketingSection>
  );
}
