"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AmbassadorDashNav } from "@/components/ambassadors/AmbassadorDashNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Select,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { buildAmbassadorReferralLink } from "@/lib/ambassador-referral";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import {
  fetchMyReferralEarnings,
  fetchMyReferralPrograms,
  fetchMyReferralSummary,
  type ReferralEarningRow,
  type ReferralProgramRow,
  type ReferralSummary,
} from "@/lib/promos-api";

function money(value: string | number | undefined): string {
  const n = Number(value ?? 0);
  return formatNgn(Number.isFinite(n) ? n : 0);
}

export default function AmbassadorDashboardOverviewPage() {
  const [summary, setSummary] = useState<ReferralSummary | null>(null);
  const [programs, setPrograms] = useState<ReferralProgramRow[]>([]);
  const [earnings, setEarnings] = useState<ReferralEarningRow[]>([]);
  const [scope, setScope] = useState("all");
  const [productType, setProductType] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void (async () => {
      setLoading(true);
      setError(null);
      try {
        const scopeParam = scope === "all" ? undefined : scope;
        const productParam = productType === "all" ? undefined : productType;
        const [s, p, e] = await Promise.all([
          fetchMyReferralSummary({
            scope: scopeParam,
            product_type: productParam,
          }),
          fetchMyReferralPrograms({ scope: scopeParam }),
          fetchMyReferralEarnings({
            scope: scopeParam,
            product_type: productParam,
          }),
        ]);
        if (!active) return;
        setSummary(s);
        setPrograms(p);
        setEarnings(e);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Could not load referral summary",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [scope, productType]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Ambassadors"
      title="Pàdéyá Ambassadors"
      description="Unified referral overview. Totals come from the commission ledger. Platform programs use one shareable link for tickets and merchandise."
      actions={
        <Link href="/ambassadors/events">
          <Button size="sm">Find events to promote</Button>
        </Link>
      }
    >
      <AmbassadorDashNav />

      {error ? (
        <Alert tone="danger" title="Unable to load">
          {error}
        </Alert>
      ) : null}

      <div className="mb-6 grid gap-3 sm:grid-cols-2">
        <Select
          label="Scope"
          value={scope}
          onChange={(e) => setScope(e.target.value)}
        >
          <option value="all">All programs</option>
          <option value="platform">Platform programs</option>
          <option value="host">Host campaigns</option>
        </Select>
        <Select
          label="Product"
          value={productType}
          onChange={(e) => setProductType(e.target.value)}
        >
          <option value="all">Tickets & merchandise</option>
          <option value="ticket">Tickets</option>
          <option value="merchandise">Merchandise</option>
        </Select>
      </div>

      {loading ? <SkeletonLoader lines={6} /> : null}

      {summary && !loading ? (
        <div className="space-y-8">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Clicks" value={summary.clicks} />
            <StatCard title="Converted orders" value={summary.converted_orders} />
            <StatCard title="Attributed items" value={summary.attributed_items} />
            <StatCard
              title="Referred sales"
              value={money(summary.referred_gross_sales)}
            />
            <StatCard
              title="Pending commission"
              value={money(summary.pending_commission)}
            />
            <StatCard
              title="Available for payout"
              value={money(summary.available_commission)}
            />
            <StatCard
              title="Paid commission"
              value={money(summary.paid_commission)}
            />
            <StatCard
              title="Reversed commission"
              value={money(summary.reversed_commission)}
            />
          </div>

          <section className="space-y-3">
            <h2 className="text-lg font-bold">Programs & campaigns</h2>
            {programs.length === 0 ? (
              <EmptyState
                title="No enrollments yet"
                description="Join an open host campaign or wait for a platform program invite."
              />
            ) : (
              <div className="space-y-3">
                {programs.map((row) => {
                  const link =
                    row.referral_link_path ||
                    (row.referral_code
                      ? buildAmbassadorReferralLink(row.referral_code, {
                          platformWide: row.scope === "platform",
                          slug: undefined,
                        })
                      : "");
                  return (
                    <Card key={row.enrollment_id} className="space-y-2 p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold">{row.name}</h3>
                        <Badge
                          tone={row.scope === "platform" ? "success" : "neutral"}
                        >
                          {row.scope_badge}
                        </Badge>
                        <Badge tone="outline">{row.status}</Badge>
                      </div>
                      {row.event_title ? (
                        <p className="text-sm text-muted-foreground">
                          Event: {row.event_title}
                        </p>
                      ) : null}
                      <p className="text-sm text-muted-foreground">
                        Covers:{" "}
                        {(row.product_coverage || []).join(", ") || "—"} · Clicks:{" "}
                        {row.clicks} · Orders: {row.converted_orders}
                      </p>
                      <p className="text-sm">
                        Pending {money(row.pending_commission)} · Available{" "}
                        {money(row.available_commission)} · Paid{" "}
                        {money(row.paid_commission)}
                      </p>
                      {link ? (
                        <div className="flex flex-wrap gap-2">
                          <code className="rounded bg-surface-muted px-2 py-1 text-xs">
                            {link}
                          </code>
                          <Button
                            size="sm"
                            variant="secondary"
                            type="button"
                            onClick={() => void navigator.clipboard.writeText(link)}
                          >
                            Copy link
                          </Button>
                        </div>
                      ) : null}
                    </Card>
                  );
                })}
              </div>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-bold">Earnings</h2>
            {earnings.length === 0 ? (
              <EmptyState
                title="No earnings yet"
                description="Commission appears here after verified paid referrals."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground">
                      <th className="py-2 pr-3">Date</th>
                      <th className="py-2 pr-3">Source</th>
                      <th className="py-2 pr-3">Program</th>
                      <th className="py-2 pr-3">Event</th>
                      <th className="py-2 pr-3">Product</th>
                      <th className="py-2 pr-3">Eligible</th>
                      <th className="py-2 pr-3">Commission</th>
                      <th className="py-2 pr-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {earnings.map((row) => (
                      <tr key={row.id} className="border-b border-border/60">
                        <td className="py-2 pr-3">
                          {row.date ? new Date(row.date).toLocaleDateString() : "—"}
                        </td>
                        <td className="py-2 pr-3">
                          <Badge
                            tone={row.source === "platform" ? "success" : "neutral"}
                          >
                            {row.source === "platform" ? "Platform" : "Host"}
                          </Badge>
                        </td>
                        <td className="py-2 pr-3">{row.program_name || "—"}</td>
                        <td className="py-2 pr-3">{row.event_title || "—"}</td>
                        <td className="py-2 pr-3">{row.product_type}</td>
                        <td className="py-2 pr-3">{money(row.eligible_sale)}</td>
                        <td className="py-2 pr-3">{money(row.commission)}</td>
                        <td className="py-2 pr-3">
                          {row.entry_type}/{row.status}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      ) : null}
    </DashboardShell>
  );
}
