"use client";

import { useEffect, useState } from "react";

import { AmbassadorDashNav } from "@/components/ambassadors/AmbassadorDashNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Card,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn, formatPercent } from "@/lib/format";
import { fetchMyAmbassadorEnrollments } from "@/lib/promos-api";
import type { AmbassadorDashboard } from "@/lib/types/promos";

/** Ranks the ambassador's own campaigns by confirmed sales performance. */
export default function AmbassadorLeaderboardPage() {
  const [rows, setRows] = useState<AmbassadorDashboard[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchMyAmbassadorEnrollments();
        const ranked = [...(data.enrollments || [])].sort((a, b) => {
          const rev =
            Number(b.revenue_generated || 0) - Number(a.revenue_generated || 0);
          if (rev !== 0) return rev;
          return (b.clicks || 0) - (a.clicks || 0);
        });
        if (active) setRows(ranked);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Could not load leaderboard",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Ambassadors"
      title="Leaderboard"
      description="Your campaigns ranked by confirmed revenue and clicks. Hosts see the full public leaderboard for each event."
    >
      <AmbassadorDashNav />

      {error ? (
        <Alert tone="danger" title="Unable to load">
          {error}
        </Alert>
      ) : null}

      {rows === null && !error ? <SkeletonLoader lines={5} /> : null}

      {rows && rows.length === 0 ? (
        <EmptyState
          title="No campaigns yet"
          description="Join an open event Ambassadors campaign to appear here."
        />
      ) : null}

      {rows && rows.length > 0 ? (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2 pr-3">Rank</th>
                <th className="py-2 pr-3">Campaign / event</th>
                <th className="py-2 pr-3">Clicks</th>
                <th className="py-2 pr-3">Sales</th>
                <th className="py-2 pr-3">Conv.</th>
                <th className="py-2 pr-3">Revenue</th>
                <th className="py-2">Est. earnings</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr
                  key={row.ambassador.id}
                  className="border-t border-border"
                >
                  <td className="py-2.5 pr-3 font-extrabold text-heading">
                    #{index + 1}
                  </td>
                  <td className="py-2.5 pr-3 font-semibold text-foreground">
                    {row.ambassador.event_title || "Campaign"}
                  </td>
                  <td className="py-2.5 pr-3">{row.clicks}</td>
                  <td className="py-2.5 pr-3">
                    {row.tickets_sold + (row.merch_units_sold || 0)}
                  </td>
                  <td className="py-2.5 pr-3">
                    {formatPercent(row.conversion_rate)}
                  </td>
                  <td className="py-2.5 pr-3">
                    {formatNgn(row.revenue_generated)}
                  </td>
                  <td className="py-2.5">{formatNgn(row.commission_owed)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </DashboardShell>
  );
}
