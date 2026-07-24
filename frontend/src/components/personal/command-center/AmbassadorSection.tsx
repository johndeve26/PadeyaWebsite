"use client";

import Link from "next/link";

import { SectionLabel } from "@/components/personal/command-center/SectionLabel";
import { Button, Card, SkeletonLoader } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import { shouldShowAmbassadorStrip } from "@/lib/personal-command-center";
import type { AmbassadorEarningsSummary } from "@/lib/types/promos";

export function AmbassadorSection({
  loading,
  summary,
}: {
  loading: boolean;
  summary: AmbassadorEarningsSummary | null;
}) {
  if (loading) {
    return (
      <section className="min-w-0 space-y-3">
        <SectionLabel>Ambassadors</SectionLabel>
        <SkeletonLoader lines={2} />
      </section>
    );
  }

  if (!shouldShowAmbassadorStrip(summary) || !summary) return null;

  return (
    <section className="min-w-0 space-y-3">
      <SectionLabel>Ambassadors</SectionLabel>
      <Card className="min-w-0 space-y-3">
        <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-base font-bold tracking-tight text-foreground sm:text-lg">
              {summary.enrollments_active > 0
                ? `${summary.enrollments_active} active campaign${summary.enrollments_active === 1 ? "" : "s"}`
                : "Promote and earn"}
            </h3>
            <p className="mt-1 break-words text-sm text-muted-foreground">
              {summary.clicks} clicks · {summary.confirmed_sales} sales ·{" "}
              {formatNgn(summary.estimated_earnings)} estimated ·{" "}
              {formatNgn(summary.payable_earnings)} payable
              {summary.payout_status_label
                ? ` · ${summary.payout_status_label}`
                : ""}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Link href="/dashboard/ambassador/links">
              <Button size="sm">Copy links</Button>
            </Link>
            <Link href="/dashboard/ambassador">
              <Button size="sm" variant="secondary">
                View Ambassadors
              </Button>
            </Link>
          </div>
        </div>
      </Card>
    </section>
  );
}
