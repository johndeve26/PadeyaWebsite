"use client";

import Link from "next/link";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { HostRecommendationsSection } from "@/components/personal/command-center/HostRecommendationsSection";
import { Button } from "@/components/ui";

export default function HostsForYouPage() {
  return (
    <DashboardShell
      tone="soft"
      compact
      eyebrow="Community"
      title="Hosts for you"
      description="Personalized Legacy hosts based on your tickets, follows, interests, and city — never private spend or hidden venues."
      actions={
        <Link href="/hosts">
          <Button size="sm" variant="secondary">
            Host marketplace
          </Button>
        </Link>
      }
    >
      <HostRecommendationsSection variant="page" limit={12} surface="dashboard_hosts_for_you" />
    </DashboardShell>
  );
}
