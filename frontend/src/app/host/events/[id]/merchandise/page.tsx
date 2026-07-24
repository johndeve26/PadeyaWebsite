"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { EventOpsNav } from "@/components/host/EventOpsNav";
import { EventMerchSubnav } from "@/components/merch/host/EventMerchSubnav";
import { HostMerchProductList } from "@/components/merch/host/HostMerchProductList";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  SkeletonLoader,
  StatCard,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import { fetchEventById, updateEvent } from "@/lib/events-api";
import {
  fetchHostMerchProducts,
  fetchHostMerchStats,
} from "@/lib/merch-api";
import type { EventItem } from "@/lib/types/events";
import type { MerchHostEventStats, MerchProduct } from "@/lib/types/merch";

const SALES_STATUS_LABEL: Record<string, string> = {
  selling: "Selling",
  paused: "Paused",
  closed: "Closed",
  no_merch: "No merch",
};

export default function EventMerchandisePage() {
  const params = useParams<{ id: string }>();
  const toast = useToast();
  const [products, setProducts] = useState<MerchProduct[] | null>(null);
  const [stats, setStats] = useState<MerchHostEventStats | null>(null);
  const [event, setEvent] = useState<EventItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savingFlag, setSavingFlag] = useState(false);

  const load = useCallback(async () => {
    const [rows, studioStats] = await Promise.all([
      fetchHostMerchProducts(params.id),
      fetchHostMerchStats(params.id),
    ]);
    setProducts(rows);
    setStats(studioStats);
  }, [params.id]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [rows, studioStats, ev] = await Promise.all([
          fetchHostMerchProducts(params.id),
          fetchHostMerchStats(params.id),
          fetchEventById(params.id),
        ]);
        if (active) {
          setProducts(rows);
          setStats(studioStats);
          setEvent(ev);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load Merch Studio",
          );
          setProducts([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  async function onToggleMerchOnly(next: boolean) {
    setSavingFlag(true);
    try {
      const updated = await updateEvent(params.id, {
        allow_merch_only_checkout: next,
      });
      setEvent(updated);
      toast.push({
        tone: "success",
        title: next
          ? "Merch-only checkout enabled"
          : "Merch-only checkout disabled",
      });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not update setting",
      );
    } finally {
      setSavingFlag(false);
    }
  }

  const title = stats?.event_title || event?.title || "Event merchandise";
  const salesLabel =
    SALES_STATUS_LABEL[stats?.sales_status ?? "no_merch"] ?? "Merch";

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title={title}
        description="Premium pickup-only merch for this event. Revenue shown here is merch line totals only — no payment gateway details."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="outline">{salesLabel}</Badge>
            <Link href={`/host/events/${params.id}/merchandise/new`}>
              <Button size="sm">Add merch</Button>
            </Link>
          </div>
        }
      >
        <EventOpsNav eventId={params.id} />
        <EventMerchSubnav eventId={params.id} />
        {error ? (
          <Alert tone="danger" title="Merch Studio error">
            {error}
          </Alert>
        ) : null}

        {stats ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <StatCard
              title="Merch revenue"
              value={formatNgn(stats.total_merch_revenue)}
              hint="Paid merch lines only"
            />
            <StatCard title="Items sold" value={stats.items_sold} />
            <StatCard title="Pending pickup" value={stats.pending_pickup} />
            <StatCard title="Picked up" value={stats.picked_up} />
            <StatCard title="Active products" value={stats.active_products} />
            <StatCard
              title="Sold out variants"
              value={stats.sold_out_variants}
            />
          </div>
        ) : products === null ? (
          <SkeletonLoader lines={3} />
        ) : null}

        <Card className="space-y-2">
          <label className="flex items-start gap-3 text-sm text-foreground">
            <input
              type="checkbox"
              className="mt-1"
              checked={Boolean(event?.allow_merch_only_checkout)}
              disabled={!event || savingFlag}
              onChange={(e) => void onToggleMerchOnly(e.target.checked)}
            />
            <span>
              <span className="font-bold">Allow merch-only checkout</span>
              <span className="mt-0.5 block text-muted-foreground">
                When off, buyers must add a ticket with merch. Ticket + merch
                carts always work.
              </span>
            </span>
          </label>
        </Card>

        <Card className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 className="text-lg font-extrabold text-foreground">
                Products
              </h2>
              <p className="text-sm text-muted-foreground">
                Edit, pause, duplicate, or archive listings.
              </p>
            </div>
            <Link href={`/host/events/${params.id}/merchandise/fulfillment`}>
              <Button size="sm" variant="secondary">
                Fulfillment desk
              </Button>
            </Link>
          </div>
          {products === null ? (
            <SkeletonLoader lines={4} />
          ) : (
            <HostMerchProductList
              products={products}
              editHref={(product) =>
                `/host/events/${params.id}/merchandise/${product.id}/edit`
              }
              onChanged={load}
            />
          )}
        </Card>
      </DashboardShell>
    </RequireHost>
  );
}
