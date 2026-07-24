"use client";

import Link from "next/link";

import type {
  CampaignReport,
  SponsorOverviewReport,
} from "@/lib/sponsor-reports-api";
import { formatNgn } from "@/lib/format";

function pct(rate: number | null): string {
  if (rate == null) return "—";
  return `${Math.round(rate * 100)}%`;
}

function StatCard({
  title,
  value,
  hint,
}: {
  title: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase text-muted-foreground">
        {title}
      </p>
      <p className="mt-1 text-2xl font-bold text-foreground">{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export function SponsorReportDashboard({
  report,
  campaignLinkPrefix,
}: {
  report: SponsorOverviewReport | CampaignReport;
  campaignLinkPrefix?: string;
}) {
  const isOverview = "campaigns_by_status" in report;
  const inq = report.inquiries;

  return (
    <div className="space-y-8">
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard title="Saved opportunities" value={report.saved_opportunities_count} />
        <StatCard title="Inquiries sent" value={inq.total} />
        <StatCard
          title="Response rate"
          value={pct(report.response_rate)}
          hint={
            report.avg_response_hours != null
              ? `Avg response ~${report.avg_response_hours}h`
              : undefined
          }
        />
        <StatCard title="Accepted" value={inq.accepted} />
        <StatCard title="Pending" value={inq.pending} />
        <StatCard title="Declined" value={inq.declined} />
        {report.linked_placements.spend_committed_ngn != null ? (
          <StatCard
            title="Spend committed"
            value={formatNgn(Number(report.linked_placements.spend_committed_ngn))}
            hint="From approved placements only"
          />
        ) : (
          <StatCard title="Linked placements" value={report.linked_placements.count} />
        )}
        {report.estimated_reach != null ? (
          <StatCard
            title="Estimated reach"
            value={report.estimated_reach.toLocaleString()}
            hint="Public-safe aggregate only"
          />
        ) : null}
        {"deals" in report && report.deals ? (
          <>
            <StatCard
              title="Deliverables pending"
              value={report.deals.deliverables_pending}
            />
            <StatCard
              title="Deliverables completed"
              value={report.deals.deliverables_completed}
            />
            <StatCard
              title="Overdue deliverables"
              value={report.deals.deliverables_overdue}
            />
            <StatCard
              title="Fulfillment rate"
              value={pct(report.deals.deliverables_completion_rate)}
            />
          </>
        ) : null}
      </section>

      <section>
        <h2 className="font-bold">Inquiry funnel</h2>
        <ul className="mt-2 grid gap-2 sm:grid-cols-3 text-sm">
          <li className="rounded-lg border border-border px-3 py-2">
            Pending: <strong>{inq.pending}</strong>
          </li>
          <li className="rounded-lg border border-border px-3 py-2">
            Accepted: <strong>{inq.accepted}</strong>
          </li>
          <li className="rounded-lg border border-border px-3 py-2">
            Declined: <strong>{inq.declined}</strong>
          </li>
        </ul>
      </section>

      {isOverview ? (
        <section>
          <h2 className="font-bold">Campaign activity</h2>
          <ul className="mt-2 flex flex-wrap gap-2 text-sm">
            {Object.entries(
              (report as SponsorOverviewReport).campaigns_by_status,
            ).map(([status, count]) => (
              <li
                key={status}
                className="rounded-full bg-muted px-3 py-1 capitalize"
              >
                {status.replace(/_/g, " ")}: {count}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="grid gap-6 md:grid-cols-2">
        <div>
          <h2 className="font-bold">Top categories</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {report.top_categories.length === 0 ? (
              <li className="text-muted-foreground">No category data yet.</li>
            ) : (
              report.top_categories.map((row) => (
                <li key={row.label}>
                  {row.label} · {row.count}
                </li>
              ))
            )}
          </ul>
        </div>
        <div>
          <h2 className="font-bold">Top locations</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {report.top_locations.length === 0 ? (
              <li className="text-muted-foreground">No location data yet.</li>
            ) : (
              report.top_locations.map((row) => (
                <li key={row.label}>
                  {row.label} · {row.count}
                </li>
              ))
            )}
          </ul>
        </div>
      </section>

      <section>
        <h2 className="font-bold">Recommendation activity</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Clicks and saves from rules-based recommendations — no fan data.
        </p>
        <ul className="mt-2 flex flex-wrap gap-3 text-sm">
          <li>Clicks: {report.recommendation_engagement.clicked}</li>
          <li>Saved: {report.recommendation_engagement.saved}</li>
          <li>Dismissed: {report.recommendation_engagement.dismissed}</li>
        </ul>
      </section>

      {report.pending_actions.length > 0 ? (
        <section>
          <h2 className="font-bold">Pending actions</h2>
          <ul className="mt-2 space-y-2">
            {report.pending_actions.map((a) => (
              <li
                key={a.kind}
                className="rounded-lg border border-border px-3 py-2 text-sm"
              >
                {a.label} ({a.count})
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {campaignLinkPrefix ? (
        <p className="text-sm">
          <Link href={campaignLinkPrefix} className="text-accent underline">
            Back to campaign
          </Link>
        </p>
      ) : null}
    </div>
  );
}
