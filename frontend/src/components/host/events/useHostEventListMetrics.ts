"use client";

import { useEffect, useState } from "react";

import { fetchHostEventAnalyticsOverview } from "@/lib/analytics-api";
import type { EventListMetrics } from "@/lib/host-events-list";
import { fetchHostMerchStats } from "@/lib/merch-api";

const BATCH_SIZE = 4;

async function mapInBatches<T>(
  ids: string[],
  worker: (id: string) => Promise<T | null>,
): Promise<Record<string, T>> {
  const out: Record<string, T> = {};
  for (let i = 0; i < ids.length; i += BATCH_SIZE) {
    const slice = ids.slice(i, i + BATCH_SIZE);
    const results = await Promise.all(
      slice.map(async (id) => {
        const value = await worker(id);
        return [id, value] as const;
      }),
    );
    for (const [id, value] of results) {
      if (value != null) out[id] = value;
    }
  }
  return out;
}

type Options = {
  eventIds: string[];
  loadAnalytics: boolean;
  loadMerch: boolean;
  showFinance: boolean;
};

export function useHostEventListMetrics({
  eventIds,
  loadAnalytics,
  loadMerch,
  showFinance,
}: Options): { metrics: Record<string, EventListMetrics>; loading: boolean } {
  const [metrics, setMetrics] = useState<Record<string, EventListMetrics>>({});
  const [loadedKey, setLoadedKey] = useState("");

  const enabled = (loadAnalytics || loadMerch) && eventIds.length > 0;
  const idsKey = eventIds.join(",");
  const loading = enabled && loadedKey !== idsKey;

  useEffect(() => {
    if (!enabled) return;

    let active = true;

    void (async () => {
      const next: Record<string, EventListMetrics> = {};

      if (loadAnalytics) {
        const analytics = await mapInBatches(eventIds, async (id) => {
          try {
            return await fetchHostEventAnalyticsOverview(id);
          } catch {
            return null;
          }
        });
        for (const [id, overview] of Object.entries(analytics)) {
          next[id] = {
            ...(next[id] ?? {}),
            tickets_sold: overview.tickets_sold,
            revenue: showFinance ? Number(overview.revenue) || 0 : undefined,
            check_in_count: overview.check_in_count,
          };
        }
      }

      if (loadMerch) {
        const merch = await mapInBatches(eventIds, async (id) => {
          try {
            return await fetchHostMerchStats(id);
          } catch {
            return null;
          }
        });
        for (const [id, stats] of Object.entries(merch)) {
          next[id] = {
            ...(next[id] ?? {}),
            merch_product_count: stats.product_count,
            merch_pending_pickup: stats.pending_pickup,
            merch_sales_status: stats.sales_status,
          };
        }
      }

      if (active) {
        setMetrics(next);
        setLoadedKey(idsKey);
      }
    })();

    return () => {
      active = false;
    };
  }, [enabled, idsKey, loadAnalytics, loadMerch, showFinance, eventIds]);

  if (!enabled) {
    return { metrics: {}, loading: false };
  }

  return { metrics, loading };
}
