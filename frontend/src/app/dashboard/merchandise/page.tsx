"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { BuyerMerchDashboard } from "@/components/merch/buyer/BuyerMerchDashboard";
import {
  Alert,
  Button,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { trackMerchPickupViewed } from "@/lib/analytics";
import {
  fetchMyEligiblePostEventDrops,
  fetchMyMerch,
} from "@/lib/merch-api";
import { cacheMerchPickupListForOffline } from "@/lib/pwa/offline-merch-cache";
import type { MerchCatalogProduct, MerchFulfillment } from "@/lib/types/merch";

export default function BuyerMerchandisePage() {
  const [rows, setRows] = useState<MerchFulfillment[] | null>(null);
  const [drops, setDrops] = useState<MerchCatalogProduct[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [items, eligible] = await Promise.all([
          fetchMyMerch(),
          fetchMyEligiblePostEventDrops().catch(() => []),
        ]);
        if (!active) return;
        cacheMerchPickupListForOffline(items);
        setRows(items);
        setDrops(eligible);
        trackMerchPickupViewed({ itemCount: items.length });
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load merchandise",
          );
          setRows([]);
          setDrops([]);
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
      compact
      title="My merch"
      description="Track pickup codes, QR passes, shipping, and official event merch orders."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/orders">
            <Button variant="secondary" size="sm">
              Orders
            </Button>
          </Link>
          <Link href="/dashboard/cart">
            <Button variant="secondary" size="sm">
              Cart
            </Button>
          </Link>
          <Link href="/dashboard/tickets">
            <Button variant="secondary" size="sm">
              Tickets
            </Button>
          </Link>
          <Link href="/events">
            <Button variant="primary" size="sm">
              Browse events
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Could not load merchandise">
          {error}
        </Alert>
      ) : null}

      {rows === null ? (
        <SkeletonLoader lines={5} />
      ) : rows.length === 0 && !(drops && drops.length) ? (
        <EmptyState
          title="No merch orders yet"
          description="Official event merch you buy on Pàdéyá will appear here."
          action={
            <Link href="/events">
              <Button size="lg">Browse events</Button>
            </Link>
          }
        />
      ) : (
        <BuyerMerchDashboard rows={rows} drops={drops || []} />
      )}
    </DashboardShell>
  );
}
