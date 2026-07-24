"use client";

import Link from "next/link";

import { Card } from "@/components/ui";
import { formatNgn } from "@/lib/format";

export type SalesSnapshotData = {
  ticketsSold: number | null;
  ticketRevenue: string | number | null;
  merchUnits: number | null;
  ambassadorConversions: number | null;
  openInquiries: number | null;
  analyticsLoaded: boolean;
  merchLoaded: boolean;
  ambassadorsLoaded: boolean;
  inquiriesLoaded: boolean;
};

export function SalesSnapshotSection({
  data,
  canViewMoney,
  canViewSponsors,
  canViewAmbassadors,
}: {
  data: SalesSnapshotData;
  canViewMoney: boolean;
  canViewSponsors: boolean;
  canViewAmbassadors: boolean;
}) {
  const {
    ticketsSold,
    ticketRevenue,
    merchUnits,
    ambassadorConversions,
    openInquiries,
    analyticsLoaded,
    merchLoaded,
    ambassadorsLoaded,
    inquiriesLoaded,
  } = data;

  return (
    <section className="space-y-3">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Sales
        </p>
        <h3 className="text-lg font-bold text-foreground">Sales snapshot</h3>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="space-y-1">
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
            Tickets (7d)
          </p>
          <p className="text-xl font-bold tabular-nums text-foreground">
            {!analyticsLoaded ? "—" : ticketsSold ?? 0}
          </p>
          <p className="text-sm text-muted-foreground">
            {canViewMoney && analyticsLoaded && ticketRevenue != null
              ? formatNgn(ticketRevenue)
              : analyticsLoaded && ticketsSold === 0
                ? "No sales yet"
                : "Portfolio snapshot"}
          </p>
        </Card>
        <Card className="space-y-1">
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
            Merch sold
          </p>
          <p className="text-xl font-bold tabular-nums text-foreground">
            {!merchLoaded ? "—" : merchUnits ?? 0}
          </p>
          <p className="text-sm text-muted-foreground">
            {merchLoaded && merchUnits === 0
              ? "No merch sales yet"
              : "Units across catalog"}
          </p>
        </Card>
        {canViewAmbassadors ? (
          <Card className="space-y-1">
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
              Ambassador conversions
            </p>
            <p className="text-xl font-bold tabular-nums text-foreground">
              {!ambassadorsLoaded ? "—" : ambassadorConversions ?? 0}
            </p>
            <p className="text-sm text-muted-foreground">
              <Link href="/host/ambassadors/conversions" className="font-semibold hover:text-accent">
                View ledger
              </Link>
            </p>
          </Card>
        ) : null}
        {canViewSponsors ? (
          <Card className="space-y-1">
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
              Sponsor inquiries
            </p>
            <p className="text-xl font-bold tabular-nums text-foreground">
              {!inquiriesLoaded ? "—" : openInquiries ?? 0}
            </p>
            <p className="text-sm text-muted-foreground">
              {inquiriesLoaded && openInquiries === 0 ? (
                "No open inquiries"
              ) : (
                <Link href="/host/sponsorships" className="font-semibold hover:text-accent">
                  Review inquiries
                </Link>
              )}
            </p>
          </Card>
        ) : null}
      </div>
    </section>
  );
}
